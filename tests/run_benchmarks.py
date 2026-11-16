import os
import sys

# Forzar salida sin búfer
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
import requests
import websockets
from kokoro_onnx import Kokoro

OLLAMA_URL = "http://127.0.0.1:11434"
WS_URL = "ws://127.0.0.1:8000/ws/chat"
MODEL_NAME = "llama3.2:3b"

results_summary = {}

def log(msg: str):
    print(msg, flush=True)

def print_header(title: str):
    log("\n" + "=" * 70)
    log(f"  🧪 {title}")
    log("=" * 70)

def print_metric(name: str, value: Any, unit: str = "", status: str = "✓"):
    log(f"  [{status}] {name:<38} : {value} {unit}")

# ==============================================================================
# TEST 1: Benchmark TTS (Kokoro-82M ONNX)
# ==============================================================================
def test_tts():
    print_header("TEST 1: Benchmark Síntesis de Voz (Kokoro-82M ONNX)")
    tts = Kokoro("models/kokoro-v0_19.onnx", "models/voices-v1.0.bin")
    
    cases = [
        {"voice": "af_sarah", "text": "Sure thing! How is your day going so far?", "desc": "Inglés (af_sarah)"},
        {"voice": "ef_dora", "text": "¡Claro que sí! ¿Cómo te encuentras el día de hoy?", "desc": "Español (ef_dora)"}
    ]
    
    synth_times = []
    rtfs = []
    
    for c in cases:
        t0 = time.perf_counter()
        samples, sr = tts.create(c["text"], voice=c["voice"], speed=1.1)
        dur_ms = (time.perf_counter() - t0) * 1000
        audio_s = len(samples) / sr
        rtf = (dur_ms / 1000) / audio_s
        synth_times.append(dur_ms)
        rtfs.append(rtf)
        
        log(f"\n  • [{c['desc']}]: \"{c['text']}\"")
        log(f"    - Duración de Audio : {audio_s:.2f} s")
        log(f"    - Tiempo Síntesis   : {dur_ms:.1f} ms")
        log(f"    - Factor RTF        : {rtf:.3f}x ({1/rtf:.1f}x más rápido que tiempo real)")
        
    avg_synth = sum(synth_times) / len(synth_times)
    avg_rtf = sum(rtfs) / len(rtfs)
    print_metric("Tiempo promedio síntesis frase", f"{avg_synth:.1f}", "ms", status="⚡")
    print_metric("Factor Tiempo Real (RTF)", f"{avg_rtf:.3f}x", f"({1/avg_rtf:.1f}x faster)")
    results_summary["tts_avg_synth_ms"] = round(avg_synth, 1)
    results_summary["tts_rtf"] = round(avg_rtf, 3)

# ==============================================================================
# TEST 2: Benchmark LLM (Ollama Llama 3.2 3B Inferencia en GPU)
# ==============================================================================
def test_llm():
    print_header("TEST 2: Benchmark LLM (Ollama Llama 3.2 3B - TTFT y Velocidad)")
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a helpful conversational tutor on a phone call. Keep responses under 18 words. Always end with a question."},
            {"role": "user", "content": "What is the best way to practice conversational English?"}
        ],
        "stream": True,
        "options": {
            "temperature": 0.6,
            "num_predict": 40
        }
    }
    
    t0 = time.perf_counter()
    res = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=12)
    
    ttft_ms = None
    tokens = []
    chunk_timestamps = []
    
    for line in res.iter_lines():
        if not line:
            continue
        now = time.perf_counter()
        data = json.loads(line.decode("utf-8"))
        delta = data.get("message", {}).get("content", "")
        if delta:
            if ttft_ms is None:
                ttft_ms = (now - t0) * 1000
            tokens.append(delta)
            chunk_timestamps.append(now)
            
    total_time_ms = (time.perf_counter() - t0) * 1000
    gen_time_s = (chunk_timestamps[-1] - chunk_timestamps[0]) if len(chunk_timestamps) > 1 else 0.1
    tps = len(tokens) / gen_time_s if gen_time_s > 0 else 0
    full_text = "".join(tokens).strip()
    
    log(f"  Respuesta generada : \"{full_text}\"")
    print_metric("Primer Token (TTFT)", f"{ttft_ms:.1f}", "ms", status="🚀" if ttft_ms < 400 else "✓")
    print_metric("Velocidad de Inferencia", f"{tps:.1f}", "tokens/s")
    print_metric("Tiempo Total de Respuesta", f"{total_time_ms:.1f}", "ms")
    print_metric("Longitud en palabras", f"{len(full_text.split())}", "palabras")
    
    results_summary["llm_ttft_ms"] = round(ttft_ms, 1)
    results_summary["llm_tps"] = round(tps, 1)
    results_summary["llm_total_ms"] = round(total_time_ms, 1)

# ==============================================================================
# TEST 3: Pipeline End-to-End WebSocket con Audio Real
# ==============================================================================
async def test_websocket_audio():
    print_header("TEST 3: Integración End-to-End con Audio Real (STT + LLM + TTS)")
    
    # Sintetizar audio WAV 16kHz
    tts = Kokoro("models/kokoro-v0_19.onnx", "models/voices-v1.0.bin")
    user_phrase = "I would like to practice speaking English for a job interview."
    samples, sr = tts.create(user_phrase, voice="af_sarah", speed=1.0)
    
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV")
    wav_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    audio_dur_s = len(samples) / sr
    
    log(f"  Voz de prueba generada : \"{user_phrase}\" ({audio_dur_s:.2f} s)")
    
    async with websockets.connect(WS_URL) as ws:
        turn_id = "bench-turn-001"
        t_start = time.perf_counter()
        
        await ws.send(json.dumps({
            "type": "audio_final",
            "turn_id": turn_id,
            "audio": wav_b64
        }))
        
        t_stt = None
        t_first_audio = None
        t_ai_done = None
        stt_reported_ms = None
        stt_text = ""
        first_sentence = ""
        audio_chunks = 0
        
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            mtype = data.get("type")
            now = time.perf_counter()
            
            if mtype == "user_transcription":
                t_stt = (now - t_start) * 1000
                stt_reported_ms = data.get("stt_ms")
                stt_text = data.get("text")
                print_metric("STT Whisper CUDA (Motor)", f"{stt_reported_ms}", "ms", status="⚡")
                print_metric("STT Round-trip WebSocket", f"{t_stt:.1f}", "ms")
                log(f"    Texto reconocido: \"{stt_text}\"")
                
            elif mtype == "audio_chunk":
                audio_chunks += 1
                if t_first_audio is None:
                    t_first_audio = (now - t_start) * 1000
                    first_sentence = data.get("text")
                    print_metric("Latencia al 1er Audio (TTFA)", f"{t_first_audio:.1f}", "ms", status="🚀")
                    log(f"    Primera oración sintetizada: \"{first_sentence}\"")
                    
            elif mtype == "ai_done":
                t_ai_done = (now - t_start) * 1000
                print_metric("Turno completo finalizado", f"{t_ai_done:.1f}", "ms")
                log(f"    Total fragmentos de audio recibidos: {audio_chunks}")
                break
                
    results_summary["stt_engine_ms"] = stt_reported_ms
    results_summary["stt_roundtrip_ms"] = round(t_stt, 1) if t_stt else 0
    results_summary["ttfa_ms"] = round(t_first_audio, 1) if t_first_audio else 0
    results_summary["e2e_total_ms"] = round(t_ai_done, 1) if t_ai_done else 0

# ==============================================================================
# TEST 4: Simulación Multi-Turno, Continuidad y Sincronización Turn ID
# ==============================================================================
async def test_multiturn():
    print_header("TEST 4: Simulación Multi-Turno y Coherencia Conversacional")
    
    script = [
        {"id": "dialog-01", "text": "Hi, I'm working as a backend developer with Python and Docker."},
        {"id": "dialog-02", "text": "I'm having trouble optimizing my database queries under heavy load."},
        {"id": "dialog-03", "text": "What are two concrete techniques I can apply today?"}
    ]
    
    async with websockets.connect(WS_URL) as ws:
        dialog_results = []
        
        for idx, step in enumerate(script, 1):
            t_id = step["id"]
            u_text = step["text"]
            log(f"\n  --- [Paso {idx}/3 | ID: {t_id}] ---")
            log(f"  👤 Usuario: \"{u_text}\"")
            
            t0 = time.perf_counter()
            await ws.send(json.dumps({"type": "text", "turn_id": t_id, "text": u_text}))
            
            ai_parts = []
            ttfa = None
            u_tr = None
            a_tr = None
            
            while True:
                raw = await ws.recv()
                data = json.loads(raw)
                mtype = data.get("type")
                now = time.perf_counter()
                
                if mtype == "ai_chunk":
                    ai_parts.append(data.get("delta", ""))
                elif mtype == "audio_chunk" and ttfa is None:
                    ttfa = (now - t0) * 1000
                elif mtype == "ai_done":
                    total_s = now - t0
                    full_ai = "".join(ai_parts).strip()
                    log(f"  🤖 IA [{total_s:.2f} s | TTFA: {ttfa:.0f} ms]: \"{full_ai}\"")
                    dialog_results.append({
                        "turn": idx, 
                        "user": u_text, 
                        "ai": full_ai, 
                        "ttfa_ms": ttfa, 
                        "total_s": total_s
                    })
                    break
                    
        # Verificar retención de contexto en Paso 3
        last_reply = dialog_results[-1]["ai"].lower()
        context_words = ["query", "database", "index", "caching", "cache", "explain", "queries", "sql", "load", "optimization"]
        has_context = any(w in last_reply for w in context_words)
        
        log("\n  • Evaluación de Coherencia Conversacional:")
        print_metric("Retención de contexto técnico", "Excelente (mencionó base de datos/queries/índices)" if has_context else "Básica", status="✓" if has_context else "⚠️")
        
        avg_turn_s = sum(r["total_s"] for r in dialog_results) / len(dialog_results)
        print_metric("Tiempo promedio por respuesta", f"{avg_turn_s:.2f}", "s", status="⚡")
        results_summary["multiturn_avg_s"] = round(avg_turn_s, 2)
        results_summary["context_retention_pass"] = has_context

# ==============================================================================
# TEST 5: Prueba de Interrupción (Barge-In)
# ==============================================================================
async def test_barge_in():
    print_header("TEST 5: Prueba de Interrupción (Barge-In / Corte Instantáneo)")
    
    async with websockets.connect(WS_URL) as ws:
        t_id = "test-interrupt-1"
        log("  1. Solicitando generación extensa para provocar habla continua...")
        await ws.send(json.dumps({
            "type": "text",
            "turn_id": t_id,
            "text": "Tell me a detailed story about exploring space and discovering distant planets."
        }))
        
        chunks = 0
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("type") == "ai_chunk":
                chunks += 1
                if chunks >= 3:
                    break
                    
        log(f"  2. IA comenzó a responder ({chunks} chunks emitidos). Disparando interrupción...")
        t_send_int = time.perf_counter()
        await ws.send(json.dumps({"type": "interrupt"}))
        
        int_lat = None
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("type") == "interrupted":
                int_lat = (time.perf_counter() - t_send_int) * 1000
                print_metric("Latencia de Corte / Interrupción", f"{int_lat:.1f}", "ms", status="⚡")
                break
                
        # Comprobar disponibilidad inmediata de GPU
        t_check = time.perf_counter()
        await ws.send(json.dumps({"type": "text", "turn_id": "test-interrupt-2", "text": "Are you ready?"}))
        
        t_recovered = None
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("type") == "ai_chunk":
                if t_recovered is None:
                    t_recovered = (time.perf_counter() - t_check) * 1000
                    print_metric("TTFT Inmediato Post-Corte", f"{t_recovered:.1f}", "ms", status="🚀")
            elif data.get("type") == "ai_done":
                break
                
        results_summary["barge_in_latency_ms"] = round(int_lat, 1)
        results_summary["post_interrupt_ttft_ms"] = round(t_recovered, 1)

# ==============================================================================
# TEST 6: Auditoría de GPU VRAM y Telemetría
# ==============================================================================
def test_gpu_telemetry():
    print_header("TEST 6: Auditoría de GPU NVIDIA RTX")
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        gpu_name = parts[0]
        vram_total = float(parts[1])
        vram_used = float(parts[2])
        vram_free = float(parts[3])
        temp = parts[4]
        util = parts[5]
        
        pct = (vram_used / vram_total) * 100
        print_metric("GPU", gpu_name)
        print_metric("VRAM Utilizada", f"{vram_used:.0f} MiB / {vram_total:.0f} MiB ({pct:.1f}%)", status="✓" if pct < 85 else "⚠️")
        print_metric("VRAM Libre", f"{vram_free:.0f}", "MiB")
        print_metric("Temperatura", f"{temp}", "°C")
        print_metric("Utilización de GPU", f"{util}", "%")
        
        results_summary["gpu_name"] = gpu_name
        results_summary["vram_used_mb"] = vram_used
        results_summary["vram_pct"] = round(pct, 1)
        results_summary["temp_c"] = temp
    except Exception as e:
        log(f"Error consultando GPU: {e}")

# ==============================================================================
# EJECUCIÓN GENERAL
# ==============================================================================
async def main():
    log("\n" + "█" * 70)
    log("  🚀 SUITE DE BENCHMARKS Y SIMULACIÓN COMPLETA DE COMPORTAMIENTO")
    log("     PROYECTO: LOCAL VOICE AI (100% LOCAL / WINDOWS RTX 4060)")
    log("█" * 70)
    
    test_tts()
    test_llm()
    await test_websocket_audio()
    await test_multiturn()
    await test_barge_in()
    test_gpu_telemetry()
    
    log("\n" + "█" * 70)
    log("  📊 RESUMEN EJECUTIVO DE TIEMPOS Y LATENCIAS")
    log("█" * 70)
    for k, v in results_summary.items():
        log(f"  • {k:<28}: {v}")
    log("█" * 70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

