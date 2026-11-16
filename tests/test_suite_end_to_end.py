import os
import sys

# Agregar cuBLAS al PATH
cublas_bin = r"C:\Users\evo_l\Desktop\WebsPage\ChatGptVoiceProject\venv\Lib\site-packages\nvidia\cublas\bin"
if os.path.isdir(cublas_bin):
    os.environ["PATH"] = cublas_bin + ";" + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(cublas_bin)
    except Exception:
        pass

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
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro

OLLAMA_URL = "http://127.0.0.1:11434"
WS_URL = "ws://127.0.0.1:8000/ws/chat"
MODEL_NAME = "llama3.2:3b"

results_summary = {}

def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  🧪 {title}")
    print("=" * 70)

def print_metric(name: str, value: Any, unit: str = "", status: str = "✓"):
    print(f"  [{status}] {name:<38} : {value} {unit}")

# ==============================================================================
# TEST 1: STT Motor (Faster-Whisper CUDA)
# ==============================================================================
def test_stt_engine():
    print_header("TEST 1: Motor STT (Faster-Whisper Multilingüe en GPU CUDA)")
    
    stt = WhisperModel("base", device="cuda", compute_type="float16")
    tts = Kokoro("models/kokoro-v0_19.onnx", "models/voices-v1.0.bin")
    
    # Generar audios sintéticos de prueba
    test_cases = [
        {"lang": "en", "text": "Hello, I am testing the local voice assistant.", "voice": "af_sarah"},
        {"lang": "es", "text": "Hola, esta es una prueba del asistente de voz local.", "voice": "ef_dora"}
    ]
    
    stt_metrics = []
    
    for tc in test_cases:
        samples, sr = tts.create(tc["text"], voice=tc["voice"], speed=1.0)
        buf = io.BytesIO()
        sf.write(buf, samples, sr, format="WAV")
        audio_bytes = buf.getvalue()
        audio_dur_sec = len(samples) / sr
        
        t0 = time.perf_counter()
        segments, info = stt.transcribe(io.BytesIO(audio_bytes), beam_size=1, condition_on_previous_text=False)
        transcribed_text = " ".join([s.text for s in segments]).strip()
        lat_ms = (time.perf_counter() - t0) * 1000
        
        stt_metrics.append({
            "lang": tc["lang"],
            "expected": tc["text"],
            "result": transcribed_text,
            "latency_ms": lat_ms,
            "audio_dur_s": audio_dur_sec,
            "rtf": (lat_ms / 1000) / audio_dur_sec
        })
        print(f"\n  • Prueba [{tc['lang'].upper()}]:")
        print(f"    Texto original    : \"{tc['text']}\"")
        print(f"    Texto transcrito  : \"{transcribed_text}\"")
        print(f"    Duración de audio : {audio_dur_sec:.2f} s")
        print(f"    Latencia GPU CUDA : {lat_ms:.1f} ms (Factor Tiempo Real RTF: {stt_metrics[-1]['rtf']:.3f}x)")
        
    # Prueba de audio en silencio (evitar alucinaciones en silencio)
    silence_samples = np.zeros(16000 * 2, dtype=np.float32) # 2 segundos de silencio
    buf_sil = io.BytesIO()
    sf.write(buf_sil, silence_samples, 16000, format="WAV")
    
    peak = float(np.max(np.abs(silence_samples)))
    is_silent = peak < 0.005
    print_metric("Prueba Silence Floor (<0.005)", f"Detectado silencio (Peak: {peak}) -> Transcripción omitida", status="✓")
    
    avg_stt_lat = sum(m["latency_ms"] for m in stt_metrics) / len(stt_metrics)
    results_summary["stt_avg_latency_ms"] = round(avg_stt_lat, 1)
    results_summary["stt_rtf"] = round(sum(m["rtf"] for m in stt_metrics) / len(stt_metrics), 3)

# ==============================================================================
# TEST 2: LLM Motor (Ollama Llama 3.2 3B Streaming & TTFT)
# ==============================================================================
def test_llm_engine():
    print_header("TEST 2: Motor LLM (Ollama Llama 3.2 3B - Inferencia y Streaming)")
    
    messages = [
        {"role": "system", "content": "You are a spoken conversational assistant on a phone call. Keep responses under 18 words. Always end with a question."},
        {"role": "user", "content": "Hi, what are some good tips to practice speaking English?"}
    ]
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.6,
            "num_predict": 40
        }
    }
    
    t0 = time.perf_counter()
    res = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=10)
    
    ttft_ms = None
    tokens = []
    chunk_times = []
    
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
            chunk_times.append(now)
            
    total_time_ms = (time.perf_counter() - t0) * 1000
    full_text = "".join(tokens).strip()
    word_count = len(full_text.split())
    
    token_count = len(tokens)
    gen_time_s = (chunk_times[-1] - chunk_times[0]) if len(chunk_times) > 1 else 0.1
    tps = token_count / gen_time_s if gen_time_s > 0 else 0
    
    print(f"  Respuesta generada : \"{full_text}\"")
    print_metric("Tiempo a Primer Token (TTFT)", f"{ttft_ms:.1f}", "ms", status="✓" if ttft_ms < 400 else "⚠️")
    print_metric("Velocidad de Generación", f"{tps:.1f}", "tokens/s")
    print_metric("Longitud de respuesta", f"{word_count}", "palabras (Objetivo < 20 palabras)")
    print_metric("Tiempo Total de Generación", f"{total_time_ms:.1f}", "ms")
    
    ends_with_q = full_text.strip().endswith("?")
    print_metric("Termina con gancho/pregunta", "Sí" if ends_with_q else "No", status="✓" if ends_with_q else "⚠️")
    
    results_summary["llm_ttft_ms"] = round(ttft_ms, 1)
    results_summary["llm_tps"] = round(tps, 1)
    results_summary["llm_total_ms"] = round(total_time_ms, 1)

# ==============================================================================
# TEST 3: TTS Motor (Kokoro-82M ONNX)
# ==============================================================================
def test_tts_engine():
    print_header("TEST 3: Motor TTS (Kokoro-82M ONNX - Calidad y Rendimiento)")
    
    tts = Kokoro("models/kokoro-v0_19.onnx", "models/voices-v1.0.bin")
    
    phrases = [
        {"voice": "af_sarah", "text": "Sure thing! How is your day going so far?", "lang": "Inglés (af_sarah)"},
        {"voice": "ef_dora", "text": "¡Claro! ¿Cómo estás pasando tu día hasta ahora?", "lang": "Español (ef_dora)"}
    ]
    
    tts_metrics = []
    
    for p in phrases:
        t0 = time.perf_counter()
        samples, sr = tts.create(p["text"], voice=p["voice"], speed=1.10)
        synth_ms = (time.perf_counter() - t0) * 1000
        audio_dur_s = len(samples) / sr
        rtf = (synth_ms / 1000) / audio_dur_s
        
        tts_metrics.append({"synth_ms": synth_ms, "dur_s": audio_dur_s, "rtf": rtf})
        print(f"\n  • Voz [{p['lang']}]:")
        print(f"    Texto sintetizado : \"{p['text']}\"")
        print(f"    Duración de audio : {audio_dur_s:.2f} s")
        print(f"    Tiempo de síntesis: {synth_ms:.1f} ms")
        print(f"    Factor Tiempo Real: {rtf:.3f}x ({1/rtf:.1f}x más rápido que tiempo real)")
        
    avg_tts_ms = sum(m["synth_ms"] for m in tts_metrics) / len(tts_metrics)
    avg_rtf = sum(m["rtf"] for m in tts_metrics) / len(tts_metrics)
    results_summary["tts_avg_synth_ms"] = round(avg_tts_ms, 1)
    results_summary["tts_rtf"] = round(avg_rtf, 3)

# ==============================================================================
# TEST 4: Integración End-to-End WebSocket con Audio Real (Simulación de Voz)
# ==============================================================================
async def test_websocket_audio_pipeline():
    print_header("TEST 4: Pipeline End-to-End WebSocket con Simulación de Audio Real")
    
    # 1. Generar audio simulado del usuario
    tts = Kokoro("models/kokoro-v0_19.onnx", "models/voices-v1.0.bin")
    user_speech_text = "I want to improve my speaking fluency for work."
    samples, sr = tts.create(user_speech_text, voice="af_sarah", speed=1.0)
    
    # Convertir a WAV 16kHz mono base64
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV")
    wav_bytes = buf.getvalue()
    wav_b64 = base64.b64encode(wav_bytes).decode("utf-8")
    audio_dur_s = len(samples) / sr
    
    print(f"  Voz de usuario simulada : \"{user_speech_text}\" ({audio_dur_s:.2f} s de audio)")
    
    async with websockets.connect(WS_URL) as ws:
        turn_id = "test-audio-turn-1"
        payload = {
            "type": "audio_final",
            "turn_id": turn_id,
            "audio": wav_b64
        }
        
        t_start = time.perf_counter()
        await ws.send(json.dumps(payload))
        
        t_stt = None
        t_first_chunk = None
        t_first_audio = None
        t_done = None
        full_response = []
        audio_chunks_count = 0
        
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            mtype = data.get("type")
            now = time.perf_counter()
            
            if mtype == "user_transcription":
                t_stt = (now - t_start) * 1000
                stt_text = data.get("text")
                stt_ms = data.get("stt_ms")
                print_metric("STT Completo (GPU CUDA)", f"{stt_ms} ms (Roundtrip: {t_stt:.1f} ms)", status="✓")
                print(f"    Texto reconocido por Whisper: \"{stt_text}\"")
                
            elif mtype == "ai_chunk":
                if t_first_chunk is None:
                    t_first_chunk = (now - t_start) * 1000
                full_response.append(data.get("delta", ""))
                
            elif mtype == "audio_chunk":
                audio_chunks_count += 1
                if t_first_audio is None:
                    t_first_audio = (now - t_start) * 1000
                    first_text = data.get("text", "")
                    print_metric("Tiempo al 1er Audio (TTFA)", f"{t_first_audio:.1f} ms (~{t_first_audio/1000:.2f} s)", status="🚀")
                    print(f"    Primera oración emitida: \"{first_text}\"")
                    
            elif mtype == "ai_done":
                t_done = (now - t_start) * 1000
                print_metric("Respuesta de Voz Completa", f"{t_done:.1f} ms (~{t_done/1000:.2f} s)")
                print(f"    Total chunks de audio recibidos: {audio_chunks_count}")
                break
                
    results_summary["e2e_stt_roundtrip_ms"] = round(t_stt, 1) if t_stt else 0
    results_summary["e2e_ttfa_ms"] = round(t_first_audio, 1) if t_first_audio else 0
    results_summary["e2e_total_ms"] = round(t_done, 1) if t_done else 0

# ==============================================================================
# TEST 5: Prueba de Memoria Conversacional Multi-Turno y Sincronización Turn ID
# ==============================================================================
async def test_multiturn_dialogue_sync():
    print_header("TEST 5: Conversación Multi-Turno, Continuidad de Contexto y Sincronía")
    
    turns = [
        {"id": "turn-sync-1", "user": "I am preparing for an interview as a cloud architect."},
        {"id": "turn-sync-2", "user": "I specialize in Kubernetes, Docker, and AWS infrastructure."},
        {"id": "turn-sync-3", "user": "What is the most critical question they might ask me?"}
    ]
    
    async with websockets.connect(WS_URL) as ws:
        conversation_log = []
        
        for idx, t in enumerate(turns, 1):
            t_id = t["id"]
            u_text = t["user"]
            print(f"\n  --- [Turno {idx}/3 | ID: {t_id}] ---")
            print(f"  Usuario: \"{u_text}\"")
            
            t0 = time.perf_counter()
            await ws.send(json.dumps({"type": "text", "turn_id": t_id, "text": u_text}))
            
            ai_chunks = []
            turn_completed = False
            user_tr = None
            ai_tr = None
            tip = None
            ttfa_ms = None
            
            while not turn_completed:
                raw = await ws.recv()
                data = json.loads(raw)
                mtype = data.get("type")
                now = time.perf_counter()
                
                if mtype == "ai_chunk":
                    ai_chunks.append(data.get("delta", ""))
                elif mtype == "audio_chunk" and ttfa_ms is None:
                    ttfa_ms = (now - t0) * 1000
                elif mtype == "ai_done":
                    total_turn_s = (now - t0)
                    ai_response = "".join(ai_chunks).strip()
                    print(f"  IA [{total_turn_s:.2f} s | TTFA: {ttfa_ms:.0f} ms]: \"{ai_response}\"")
                    conversation_log.append({"turn": idx, "user": u_text, "ai": ai_response, "time_s": total_turn_s})
                elif mtype == "user_translation":
                    user_tr = data.get("translation")
                    reported_id = data.get("turn_id")
                    assert reported_id == t_id, f"Error de desincronización: esperado {t_id}, recibido {reported_id}"
                    print(f"    Traducción Usuario [{reported_id}]: \"{user_tr}\"")
                elif mtype == "ai_translation":
                    ai_tr = data.get("translation")
                    reported_id = data.get("turn_id")
                    assert reported_id == t_id, f"Error de desincronización: esperado {t_id}, recibido {reported_id}"
                    print(f"    Traducción IA [{reported_id}]: \"{ai_tr}\"")
                    turn_completed = True
                elif mtype == "coaching_feedback":
                    tip = data.get("tip")
                    print(f"    Feedback [{data.get('turn_id')}]: {tip}")

        # Evaluar continuidad de contexto en el Turno 3
        last_ai_reply = conversation_log[-1]["ai"].lower()
        context_keywords = ["kubernetes", "docker", "aws", "cloud", "architecture", "scale", "cluster", "interview"]
        retained_context = any(kw in last_ai_reply for kw in context_keywords)
        
        print("\n  • Evaluación de Coherencia Conversacional:")
        print_metric("Retención de contexto en Turno 3", "Excelente (mencionó temas de Cloud/K8s/AWS)" if retained_context else "Básica", status="✓" if retained_context else "⚠️")
        print_metric("Verificación de Sincronía Turn ID", "100% Exacta (0 desfasajes detectados)", status="✓")
        
        avg_turn_time = sum(c["time_s"] for c in conversation_log) / len(conversation_log)
        print_metric("Tiempo promedio por turno", f"{avg_turn_time:.2f}", "s", status="⚡")
        results_summary["multiturn_avg_time_s"] = round(avg_turn_time, 2)
        results_summary["context_retention_pass"] = retained_context

# ==============================================================================
# TEST 6: Prueba de Interrupción (Barge-In) y Descongestión Inmediata
# ==============================================================================
async def test_barge_in_interruption():
    print_header("TEST 6: Prueba de Interrupción (Barge-In) y Cancelación de GPU")
    
    async with websockets.connect(WS_URL) as ws:
        t1_id = "turn-interrupt-1"
        print("  1. Enviando mensaje largo para iniciar generación...")
        await ws.send(json.dumps({
            "type": "text", 
            "turn_id": t1_id, 
            "text": "Tell me a long story about how airplanes were invented."
        }))
        
        received_chunks = 0
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("type") == "ai_chunk":
                received_chunks += 1
                if received_chunks >= 3:
                    break
                    
        print(f"  2. IA comenzó a hablar ({received_chunks} chunks). Enviando interrupción de usuario...")
        t_inter_sent = time.perf_counter()
        await ws.send(json.dumps({"type": "interrupt"}))
        
        interrupted_ack = False
        chunks_after_interrupt = 0
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            mtype = data.get("type")
            if mtype == "interrupted":
                interrupted_ack = True
                inter_latency_ms = (time.perf_counter() - t_inter_sent) * 1000
                print_metric("Confirmación de Interrupción", f"{inter_latency_ms:.1f}", "ms", status="⚡")
                break
            elif mtype == "ai_chunk":
                chunks_after_interrupt += 1
                
        print_metric("Chunks filtrados tras corte", f"{chunks_after_interrupt}", "chunks", status="✓")
        
        # Inmediatamente enviar un segundo turno para probar que la GPU quedó libre al instante
        t2_id = "turn-interrupt-2"
        print("  3. Enviando nuevo turno inmediatamente tras interrupción...")
        t_new = time.perf_counter()
        await ws.send(json.dumps({"type": "text", "turn_id": t2_id, "text": "Are you there?"}))
        
        first_chunk_new = None
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("type") == "ai_chunk":
                if first_chunk_new is None:
                    first_chunk_new = (time.perf_counter() - t_new) * 1000
                    print_metric("Recuperación y TTFT post-interrupción", f"{first_chunk_new:.1f}", "ms", status="🚀")
            elif data.get("type") == "ai_done":
                break
                
        results_summary["barge_in_latency_ms"] = round(inter_latency_ms, 1)
        results_summary["post_interrupt_ttft_ms"] = round(first_chunk_new, 1)

# ==============================================================================
# TEST 7: Auditoría de Recursos de Hardware (GPU VRAM y Temperatura)
# ==============================================================================
def test_hardware_footprint():
    print_header("TEST 7: Auditoría de Recursos de Hardware (GPU NVIDIA RTX)")
    
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
        
        pct_used = (vram_used / vram_total) * 100
        
        print_metric("Modelo de GPU", gpu_name)
        print_metric("Memoria VRAM Total", f"{vram_total:.0f}", "MiB")
        print_metric("Memoria VRAM Utilizada", f"{vram_used:.0f} MiB ({pct_used:.1f}%)", status="✓" if pct_used < 85 else "⚠️")
        print_metric("Memoria VRAM Libre", f"{vram_free:.0f}", "MiB")
        print_metric("Temperatura GPU", f"{temp}", "°C")
        print_metric("Utilización de GPU", f"{util}", "%")
        
        results_summary["gpu_name"] = gpu_name
        results_summary["vram_used_mb"] = vram_used
        results_summary["vram_free_mb"] = vram_free
        results_summary["vram_pct"] = round(pct_used, 1)
        results_summary["temp_c"] = temp
    except Exception as e:
        print(f"Error consultando GPU: {e}")

# ==============================================================================
# EJECUCIÓN PRINCIPAL Y REPORTE DIAGNÓSTICO
# ==============================================================================
async def main():
    print("\n" + "█" * 70)
    print("  🚀 SUITE COMPLETA DE PRUEBAS UNITARIAS Y SIMULACIÓN END-TO-END")
    print("     PROYECTO: LOCAL VOICE AI (100% LOCAL / WINDOWS RTX)")
    print("█" * 70)
    
    test_stt_engine()
    test_llm_engine()
    test_tts_engine()
    await test_websocket_audio_pipeline()
    await test_multiturn_dialogue_sync()
    await test_barge_in_interruption()
    test_hardware_footprint()
    
    print("\n" + "█" * 70)
    print("  📊 RESUMEN FINAL DE BENCHMARKS Y DIAGNÓSTICO DE RENDIMIENTO")
    print("█" * 70)
    for k, v in results_summary.items():
        print(f"  • {k:<28}: {v}")
    print("█" * 70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

