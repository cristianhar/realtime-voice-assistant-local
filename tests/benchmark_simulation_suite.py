import os
import sys

os.environ["PYTHONUNBUFFERED"] = "1"

import io
import time
import json
import base64
import asyncio
import subprocess
from typing import Dict, Any, List

import numpy as np
import soundfile as sf
import websockets
from kokoro_onnx import Kokoro

WS_URL = "ws://127.0.0.1:8000/ws/chat"
tts = None

def get_tts():
    global tts
    if tts is None:
        tts = Kokoro("models/kokoro-v0_19.onnx", "models/voices-v1.0.bin")
    return tts

def create_audio_b64(text: str, voice: str = "af_sarah") -> tuple[str, float]:
    engine = get_tts()
    samples, sr = engine.create(text, voice=voice, speed=1.0)
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV")
    audio_dur = len(samples) / sr
    return base64.b64encode(buf.getvalue()).decode("utf-8"), audio_dur

def log(msg: str):
    print(msg, flush=True)

def section(title: str):
    log("\n" + "=" * 75)
    log(f"  🎯 {title}")
    log("=" * 75)

# ==============================================================================
# ESCENARIO 1: Saludo Rápido y Medición Micro a Micro de Latencias
# ==============================================================================
async def run_scenario_fast_greeting() -> dict:
    section("ESCENARIO 1: Saludo Rápido y Medición de Tiempos Milestone a Milestone")
    
    phrase = "Hey! How's your morning going today?"
    b64_audio, audio_dur = create_audio_b64(phrase, "af_sarah")
    log(f"  [Entrada de Audio] \"{phrase}\" ({audio_dur:.2f} s)")
    
    async with websockets.connect(WS_URL) as ws:
        turn_id = "sc1-fast-greeting"
        t0 = time.perf_counter()
        
        await ws.send(json.dumps({
            "type": "audio_final",
            "turn_id": turn_id,
            "audio": b64_audio
        }))
        
        t_stt = None
        t_first_chunk = None
        t_first_audio = None
        t_ai_done = None
        stt_internal_ms = None
        chunks_count = 0
        ai_text = []
        
        while True:
            raw = await ws.recv()
            d = json.loads(raw)
            now = time.perf_counter()
            mtype = d.get("type")
            
            if mtype == "user_transcription":
                t_stt = (now - t0) * 1000
                stt_internal_ms = d.get("stt_ms")
                log(f"  ⏱️ [T1: STT Whisper] Transcrito en {stt_internal_ms} ms (Round-trip: {t_stt:.1f} ms) -> \"{d.get('text')}\"")
                
            elif mtype == "ai_chunk":
                if t_first_chunk is None:
                    t_first_chunk = (now - t0) * 1000
                    log(f"  ⏱️ [T2: Primer Token LLM] TTFT: {t_first_chunk:.1f} ms")
                ai_text.append(d.get("delta", ""))
                
            elif mtype == "audio_chunk":
                chunks_count += 1
                if t_first_audio is None:
                    t_first_audio = (now - t0) * 1000
                    log(f"  ⏱️ [T3: PRIMER AUDIO (TTFA)] {t_first_audio:.1f} ms (~{t_first_audio/1000:.2f} s) -> \"{d.get('text')}\"")
                    
            elif mtype == "ai_done":
                t_ai_done = (now - t0) * 1000
                full_ai = "".join(ai_text).strip()
                log(f"  ⏱️ [T4: Turno Completo] {t_ai_done:.1f} ms (~{t_ai_done/1000:.2f} s) -> Total chunks: {chunks_count}")
                log(f"  🤖 Respuesta Final: \"{full_ai}\"")
                break
                
        return {
            "stt_ms": stt_internal_ms,
            "stt_roundtrip_ms": round(t_stt, 1),
            "ttft_ms": round(t_first_chunk, 1),
            "ttfa_ms": round(t_first_audio, 1),
            "total_ms": round(t_ai_done, 1)
        }

# ==============================================================================
# ESCENARIO 2: Diálogo Técnico Multi-Turno y Coherencia de Contexto
# ==============================================================================
async def run_scenario_multiturn() -> list:
    section("ESCENARIO 2: Conversación Técnica Multi-Turno (3 Pasos Consecutivos)")
    
    turns = [
        {"id": "sc2-t1", "user": "I am practicing for a technical interview as a cloud architect."},
        {"id": "sc2-t2", "user": "The company uses Kubernetes, Docker, and AWS microservices."},
        {"id": "sc2-t3", "user": "What is the most critical question they might ask me?"}
    ]
    
    dialogue_metrics = []
    
    async with websockets.connect(WS_URL) as ws:
        for i, t in enumerate(turns, 1):
            log(f"\n  --- [Turno {i}/3 | ID: {t['id']}] ---")
            log(f"  👤 Usuario: \"{t['user']}\"")
            
            t0 = time.perf_counter()
            await ws.send(json.dumps({"type": "text", "turn_id": t["id"], "text": t["user"]}))
            
            ai_parts = []
            ttfa = None
            total_time = None
            
            while True:
                raw = await ws.recv()
                d = json.loads(raw)
                mtype = d.get("type")
                now = time.perf_counter()
                
                if mtype == "ai_chunk":
                    ai_parts.append(d.get("delta", ""))
                elif mtype == "audio_chunk" and ttfa is None:
                    ttfa = (now - t0) * 1000
                    log(f"    🔊 Primer Audio (TTFA): {ttfa:.1f} ms -> \"{d.get('text')}\"")
                elif mtype == "ai_done":
                    total_time = now - t0
                    full_resp = "".join(ai_parts).strip()
                    log(f"    ✅ Respuesta Completa [{total_time:.2f} s]: \"{full_resp}\"")
                    dialogue_metrics.append({
                        "turn": i,
                        "user": t["user"],
                        "ai": full_resp,
                        "ttfa_ms": round(ttfa, 1) if ttfa else 0,
                        "total_s": round(total_time, 2)
                    })
                    break
                    
    return dialogue_metrics

# ==============================================================================
# ESCENARIO 3: Emulación de Interrupción en Vivo (Barge-In)
# ==============================================================================
async def run_scenario_barge_in() -> dict:
    section("ESCENARIO 3: Emulación de Interrupción en Vivo (Barge-In)")
    
    async with websockets.connect(WS_URL) as ws:
        log("  1. Usuario hace una pregunta abierta para que la IA hable...")
        t0 = time.perf_counter()
        await ws.send(json.dumps({
            "type": "text",
            "turn_id": "sc3-int-01",
            "text": "Can you explain how jet engines work in full detail?"
        }))
        
        chunk_count = 0
        while True:
            raw = await ws.recv()
            d = json.loads(raw)
            if d.get("type") == "ai_chunk":
                chunk_count += 1
                if chunk_count >= 2:
                    break
                    
        log(f"  2. IA comenzó a responder ({chunk_count} chunks emitidos). Usuario INTERRUMPE hablando...")
        t_int = time.perf_counter()
        await ws.send(json.dumps({"type": "interrupt"}))
        
        int_ack_ms = None
        while True:
            raw = await ws.recv()
            d = json.loads(raw)
            if d.get("type") == "interrupted":
                int_ack_ms = (time.perf_counter() - t_int) * 1000
                log(f"  ⚡ [Corte Confirmado por Servidor] Latencia de cancelación: {int_ack_ms:.1f} ms")
                break
                
        # Turno inmediato después de la interrupción
        log("  3. Usuario formula inmediatamente una nueva pregunta: \"Wait, what is 2 plus 2?\"")
        t_new = time.perf_counter()
        await ws.send(json.dumps({
            "type": "text",
            "turn_id": "sc3-int-02",
            "text": "Wait, what is 2 plus 2?"
        }))
        
        post_ttft = None
        post_ttfa = None
        new_resp = []
        
        while True:
            raw = await ws.recv()
            d = json.loads(raw)
            now = time.perf_counter()
            mtype = d.get("type")
            
            if mtype == "ai_chunk":
                if post_ttft is None:
                    post_ttft = (now - t_new) * 1000
                    log(f"  🚀 [TTFT Post-Corte] {post_ttft:.1f} ms")
                new_resp.append(d.get("delta", ""))
            elif mtype == "audio_chunk" and post_ttfa is None:
                post_ttfa = (now - t_new) * 1000
                log(f"  🔊 [Primer Audio Post-Corte] {post_ttfa:.1f} ms -> \"{d.get('text')}\"")
            elif mtype == "ai_done":
                log(f"  ✅ [Completado Post-Corte] \"{''.join(new_resp).strip()}\"")
                break
                
        return {
            "interrupt_latency_ms": round(int_ack_ms, 1),
            "post_ttft_ms": round(post_ttft, 1) if post_ttft else 0,
            "post_ttfa_ms": round(post_ttfa, 1) if post_ttfa else 0
        }

# ==============================================================================
# ESCENARIO 4: Modo Español Nativo (Cambio de Modo en Caliente)
# ==============================================================================
async def run_scenario_spanish_mode() -> dict:
    section("ESCENARIO 4: Modo Asistente Español Nativo (Voz ef_dora)")
    
    phrase_es = "¿Qué me recomiendas hacer hoy para relajarme un poco?"
    b64_audio_es, dur_es = create_audio_b64(phrase_es, "ef_dora")
    
    async with websockets.connect(WS_URL) as ws:
        # Cambiar modo
        log("  1. Enviando evento de cambio de modo: 'es'")
        await ws.send(json.dumps({"type": "set_mode", "mode": "es"}))
        raw = await ws.recv()
        d = json.loads(raw)
        log(f"  ✓ Modo confirmado: {d.get('mode')}")
        
        # Enviar audio en español
        log(f"  2. Enviando audio en español: \"{phrase_es}\" ({dur_es:.2f} s)")
        t0 = time.perf_counter()
        await ws.send(json.dumps({
            "type": "audio_final",
            "turn_id": "sc4-es-01",
            "audio": b64_audio_es
        }))
        
        stt_es = None
        ttfa_es = None
        total_es = None
        resp_es = []
        
        while True:
            raw = await ws.recv()
            d = json.loads(raw)
            now = time.perf_counter()
            mtype = d.get("type")
            
            if mtype == "user_transcription":
                stt_es = d.get("stt_ms")
                log(f"  🎙️ Whisper STT [Español]: {stt_es} ms -> \"{d.get('text')}\"")
            elif mtype == "ai_chunk":
                resp_es.append(d.get("delta", ""))
            elif mtype == "audio_chunk" and ttfa_es is None:
                ttfa_es = (now - t0) * 1000
                log(f"  🔊 Primer Audio Español (ef_dora): {ttfa_es:.1f} ms -> \"{d.get('text')}\"")
            elif mtype == "ai_done":
                total_es = (now - t0) * 1000
                log(f"  ✅ Respuesta en Español: \"{''.join(resp_es).strip()}\"")
                break
                
        return {
            "stt_es_ms": stt_es,
            "ttfa_es_ms": round(ttfa_es, 1) if ttfa_es else 0,
            "total_es_ms": round(total_es, 1) if total_es else 0
        }

# ==============================================================================
# ESCENARIO 5: Telemetría de Hardware en Vivo
# ==============================================================================
def run_scenario_telemetry() -> dict:
    section("ESCENARIO 5: Telemetría de GPU, Estado de Potencia y Relojes")
    
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,pstate,power.draw,power.limit,memory.used,memory.total,temperature.gpu,utilization.gpu", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        res = {
            "gpu": parts[0],
            "pstate": parts[1],
            "pwr_draw_w": parts[2],
            "pwr_limit_w": parts[3],
            "vram_used_mb": parts[4],
            "vram_total_mb": parts[5],
            "temp_c": parts[6],
            "util_pct": parts[7]
        }
        for k, v in res.items():
            log(f"  • {k:<16}: {v}")
        return res
    except Exception as e:
        log(f"Error en telemetría: {e}")
        return {}

# ==============================================================================
# MAIN EJECUTOR
# ==============================================================================
async def main():
    log("\n" + "█" * 75)
    log("  🚀 SIMULADOR INTEGRAL DE SISTEMA DE TURNOS, TIMERS E INTERRUPCIONES")
    log("     LOCAL VOICE AI — AUDITORÍA COMPLETA DE LATENCIAS Y COMPORTAMIENTO")
    log("█" * 75)
    
    m1 = await run_scenario_fast_greeting()
    m2 = await run_scenario_multiturn()
    m3 = await run_scenario_barge_in()
    m4 = await run_scenario_spanish_mode()
    m5 = run_scenario_telemetry()
    
    log("\n" + "█" * 75)
    log("  📋 RESUMEN GENERAL DE DIAGNÓSTICO")
    log("█" * 75)
    log(f"  1. Saludo Rápido     : STT {m1.get('stt_ms')}ms | TTFT {m1.get('ttft_ms')}ms | TTFA {m1.get('ttfa_ms')}ms")
    log(f"  2. Multi-Turno Prom. : TTFA {sum(t['ttfa_ms'] for t in m2)/len(m2):.0f}ms | Duración Turno {sum(t['total_s'] for t in m2)/len(m2):.2f}s")
    log(f"  3. Interrupción      : Cancelación {m3.get('interrupt_latency_ms')}ms | Recuperación TTFT {m3.get('post_ttft_ms')}ms")
    log(f"  4. Español           : STT {m4.get('stt_es_ms')}ms | TTFA {m4.get('ttfa_es_ms')}ms")
    log(f"  5. GPU P-State       : Estado {m5.get('pstate')} ({m5.get('pwr_draw_w')}W / {m5.get('pwr_limit_w')}W) | Temp {m5.get('temp_c')}°C")
    log("█" * 75 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

