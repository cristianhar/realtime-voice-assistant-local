import os
import sys

# Agregar cuBLAS al PATH y cargar DLLs para aceleración en GPU CUDA
cublas_bin = r"C:\Users\evo_l\Desktop\WebsPage\ChatGptVoiceProject\venv\Lib\site-packages\nvidia\cublas\bin"
if os.path.isdir(cublas_bin):
    os.environ["PATH"] = cublas_bin + ";" + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(cublas_bin)
    except Exception:
        pass

import io
import re
import time
import json
import base64
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional

import numpy as np
import requests
import soundfile as sf
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro
import onnxruntime as ort

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL_NAME = "llama3.2:3b"

# Prompts refinados para conversación fluida y natural (Estilo llamada ChatGPT)
PROMPTS = {
    "en": """You are an engaging native English conversation partner on a real-time voice call.
RULES:
1. Always speak in natural, conversational English.
2. Keep responses very short and spoken: 1 to 2 sentences (under 15 words).
3. Sound like a lively, real person on the phone. Never use bullet points, numbered lists, asterisks, or markdown.
4. Keep the conversation flowing smoothly based on the chat history.
5. If the user makes an obvious English mistake, gently and naturally model the correct phrase.
6. Always end with a short, friendly question to invite the user to speak.""",

    "es": """Eres un compañero de conversación amigable, cálido y espontáneo en una llamada de voz en tiempo real.
REGLAS:
1. Habla SIEMPRE en español nativo, totalmente natural y fluido, como un amigo de confianza por teléfono.
2. Respuestas MUY BREVES: exactamente 1 o 2 oraciones cortas (menos de 15 a 18 palabras).
3. Tono cercano, fresco y humano. Jamás uses listas, viñetas, emojis ni asteriscos de acciones (nunca pongas *sonríe* ni *laughs*).
4. Mantén la continuidad fluida del tema del que venían hablando.
5. Concluye siempre con una pregunta casual o comentario para mantener la charla viva.""",

    "auto": """You are an intuitive bilingual conversational partner on a real-time voice call.
RULES:
1. Respond in the same language the user spoke to you (Spanish or English).
2. Keep responses natural, warm, and concise: 1 to 2 sentences (under 15 words).
3. Never use markdown, bullet points, asterisks, or emojis.
4. Maintain seamless conversational continuity and end with a friendly question."""
}

stt_model = None
tts_model = None
thread_pool = ThreadPoolExecutor(max_workers=4)

def init_models():
    global stt_model, tts_model
    print("=" * 60)
    print("Inicializando modelos BILINGÜES con Llama 3.2 3B...")
    
    # 1. Cargar Faster-Whisper Multilingual ("base") en GPU CUDA
    print("[1/2] Faster-Whisper Multilingüe en GPU CUDA...")
    try:
        stt_model = WhisperModel("base", device="cuda", compute_type="float16")
        list(stt_model.transcribe(np.zeros(16000, dtype=np.float32), beam_size=1)[0])
        print("✓ Faster-Whisper Multilingüe activo en GPU CUDA (~25ms)")
    except Exception as e:
        print(f"[Aviso] Fallback a CPU int8: {e}")
        stt_model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4)
        print("✓ Faster-Whisper Multilingüe activo en CPU (int8)")

    # 2. Cargar Kokoro TTS con ONNX multihilo optimizado (4x más rápido en CPU)
    print("[2/2] Kokoro TTS (ONNX multihilo optimizado)...")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 6
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess = ort.InferenceSession("models/kokoro-v0_19.onnx", sess_options=opts, providers=["CPUExecutionProvider"])
    tts_model = Kokoro.from_session(sess, "models/voices-v1.0.bin")
    print("✓ Kokoro listo con sesión multihilo de alto rendimiento (~450ms)")
    print("✓ Modelo LLM principal:", MODEL_NAME)
    print("=" * 60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_models()
    yield

app = FastAPI(title="Local Voice Assistant - Llama 3.2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def is_text_spanish(text: str) -> bool:
    """Heurística rápida para detectar si un texto corto es español o inglés."""
    spanish_chars = set("áéíóúüñ¿¡")
    if any(c in spanish_chars for c in text.lower()):
        return True
    spanish_words = {
        "hola", "cómo", "como", "estás", "estas", "qué", "que", "buenos", "días",
        "gracias", "por", "favor", "sí", "si", "no", "bien", "amigo", "para", "pero",
        "buenas", "tardes", "noches", "claro", "mucho", "gusto", "ayuda", "puedo", "hacer", "estoy"
    }
    words = set(re.findall(r'\b\w+\b', text.lower()))
    return len(words.intersection(spanish_words)) > 0

def clean_tts_text(text: str) -> str:
    """Limpia el texto antes de la síntesis para evitar que Kokoro lea símbolos o emojis literalmente."""
    if not text:
        return ""
    # 1. Eliminar acciones narrativas entre asteriscos o paréntesis (*sonríe*, (risas))
    t = re.sub(r'\*.*?\*', '', text)
    t = re.sub(r'\(.*?\)', '', t)
    # 2. Eliminar emojis y caracteres no fonéticos, preservando signos y acentos en español
    t = re.sub(r'[^\w\s.,!?:;¿¡áéíóúÁÉÍÓÚñÑüÜ\'\"-]', '', t)
    # 3. Normalizar espacios
    return re.sub(r'\s+', ' ', t).strip()

def synthesize_audio_wav_base64(text: str, voice_name: str = "ef_dora", lang: str = "auto") -> str:
    text_clean = clean_tts_text(text)
    if not text_clean or not tts_model:
        return ""
    actual_lang = "es"
    try:
        # Determinar idioma exacto para el fonemizador G2P nativo de Kokoro
        if lang == "auto":
            is_es = voice_name.startswith("e") or is_text_spanish(text_clean)
            actual_lang = "es" if is_es else "en-us"
        else:
            actual_lang = "es" if lang == "es" else "en-us"

        # Cadencia y velocidad natural:
        # En español 1.08x preserva la dicción y ritmo de las vocales nativas sin acelerar
        # En inglés 1.12x mantiene el ritmo conversacional dinámico
        speed = 1.08 if actual_lang == "es" else 1.12

        samples, sr = tts_model.create(
            text_clean,
            voice=voice_name,
            speed=speed,
            lang=actual_lang,
            sentence_pause=0.2,
            clause_pause=0.1
        )
        buf = io.BytesIO()
        sf.write(buf, samples, sr, format='WAV')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    except Exception as e:
        print(f"Error en síntesis TTS ({voice_name}, lang={actual_lang}): {e}")
        return ""

def transcribe_audio_bytes(audio_bytes: bytes, lang_mode: str = "auto") -> tuple[str, int, str]:
    t0 = time.time()
    try:
        data, sr = sf.read(io.BytesIO(audio_bytes))
        peak = float(np.max(np.abs(data)))
        rms = float(np.sqrt(np.mean(data**2)))
        
        # Filtro de respiración y ruido de fondo:
        # Si el audio no tiene energía vocal real (ej. respiración, suspiro o ventilador), ignorar
        if peak < 0.02 or rms < 0.005:
            return "", 0, ""

        buf = io.BytesIO(audio_bytes)
        
        whisper_lang = None
        if lang_mode == "en":
            whisper_lang = "en"
        elif lang_mode == "es":
            whisper_lang = "es"

        segments, info = stt_model.transcribe(
            buf,
            language=whisper_lang,
            beam_size=1,
            condition_on_previous_text=False,
            no_speech_threshold=0.6
        )
        text = " ".join([segment.text for segment in segments]).strip()
        latency_ms = round((time.time() - t0) * 1000)
        detected_lang = info.language if info else (lang_mode if lang_mode != "auto" else "en")
        print(f"-> STT ({latency_ms} ms) [{detected_lang}]: \"{text}\"")
        return text, latency_ms, detected_lang
    except Exception as e:
        print(f"Error en STT: {e}")
        return "", 0, "en"

def fast_analyze_turn(user_text: str, ai_text: str) -> dict:
    """Ejecuta en una sola llamada JSON ligera la traducción de ambos turnos y el tip pedagógico."""
    if not user_text.strip() or not ai_text.strip():
        return {}
    try:
        prompt = f"""Task: Translate User English to natural Spanish, translate AI English to natural Spanish, and analyze if the user made an English grammar/phrasing mistake.
User English: "{user_text}"
AI English: "{ai_text}"

Respond ONLY with valid JSON matching this schema:
{{"user_tr": "Spanish translation of User", "ai_tr": "Spanish translation of AI", "tip": "Short friendly tip in Spanish if user had an error, or null if natural"}}"""

        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "num_ctx": 1024,
                "temperature": 0.2,
                "num_predict": 90
            }
        }
        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=7)
        if res.status_code == 200:
            raw = res.json().get("response", "{}")
            return json.loads(raw)
    except Exception as e:
        print(f"[Aviso] Error en análisis post-turno: {e}")
    return {}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("static/index.html")

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✓ Cliente conectado al WebSocket.")
    
    current_mode = "en"
    current_spanish_voice = "ef_dora"
    current_english_voice = "af_sarah"
    conversation_history: List[Dict[str, str]] = [
        {"role": "system", "content": PROMPTS[current_mode]}
    ]
    
    current_generation_id = 0
    is_interrupted = False
    active_analysis_task: Optional[asyncio.Task] = None
    stt_busy = False

    def cancel_background_analysis():
        nonlocal active_analysis_task
        if active_analysis_task and not active_analysis_task.done():
            active_analysis_task.cancel()
            active_analysis_task = None

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "set_mode":
                cancel_background_analysis()
                new_mode = data.get("mode", "en")
                if new_mode in PROMPTS:
                    current_mode = new_mode
                    conversation_history = [{"role": "system", "content": PROMPTS[current_mode]}]
                    print(f"Modo cambiado a: {current_mode}")
                    await websocket.send_json({"type": "mode_changed", "mode": current_mode})
                continue

            if msg_type == "set_voice":
                new_voice = data.get("voice", "")
                if new_voice:
                    if new_voice.startswith("e"):
                        current_spanish_voice = new_voice
                    else:
                        current_english_voice = new_voice
                    print(f"Voz configurada -> ES: {current_spanish_voice}, EN: {current_english_voice}")
                    await websocket.send_json({
                        "type": "voice_changed",
                        "spanish_voice": current_spanish_voice,
                        "english_voice": current_english_voice
                    })
                continue

            if msg_type == "interrupt":
                print("⚡ Interrupción recibida del cliente (Barge-in).")
                cancel_background_analysis()
                is_interrupted = True
                current_generation_id += 1
                await websocket.send_json({"type": "interrupted"})
                continue

            user_text = ""
            stt_latency = 0
            detected_lang = "en"
            turn_id = data.get("turn_id") or f"turn-{int(time.time() * 1000)}"

            if msg_type == "audio_partial":
                if stt_busy:
                    continue
                cancel_background_analysis()
                audio_base64 = data.get("audio", "")
                if not audio_base64:
                    continue
                audio_bytes = base64.b64decode(audio_base64)
                loop = asyncio.get_running_loop()
                try:
                    stt_busy = True
                    partial_text, _, detected_lang = await loop.run_in_executor(
                        thread_pool, transcribe_audio_bytes, audio_bytes, current_mode
                    )
                    if partial_text:
                        await websocket.send_json({
                            "type": "user_partial_transcription",
                            "text": partial_text,
                            "lang": detected_lang
                        })
                finally:
                    stt_busy = False
                continue

            if msg_type in ["audio", "audio_final"]:
                cancel_background_analysis()
                audio_base64 = data.get("audio", "")
                if not audio_base64:
                    continue
                audio_bytes = base64.b64decode(audio_base64)
                await websocket.send_json({"type": "status", "state": "transcribing"})
                
                loop = asyncio.get_running_loop()
                try:
                    stt_busy = True
                    user_text, stt_latency, detected_lang = await loop.run_in_executor(
                        thread_pool, transcribe_audio_bytes, audio_bytes, current_mode
                    )
                finally:
                    stt_busy = False

                if not user_text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No se distinguió tu voz con suficiente claridad."
                    })
                    await websocket.send_json({"type": "status", "state": "idle"})
                    continue

            elif msg_type == "text":
                cancel_background_analysis()
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue
                detected_lang = "es" if is_text_spanish(user_text) else "en"

            # 1. Enviar transcripción final al cliente con su turn_id unívoco
            await websocket.send_json({
                "type": "user_transcription",
                "turn_id": turn_id,
                "text": user_text,
                "stt_ms": stt_latency,
                "lang": detected_lang
            })

            # Turno de la IA (Prioridad Absoluta de GPU)
            conversation_history.append({"role": "user", "content": user_text})
            # Mantener contexto conversacional de las últimas 8 intervenciones
            if len(conversation_history) > 9:
                conversation_history = [conversation_history[0]] + conversation_history[-8:]

            current_generation_id += 1
            gen_id = current_generation_id
            is_interrupted = False

            await websocket.send_json({"type": "status", "state": "thinking"})

            payload = {
                "model": MODEL_NAME,
                "messages": conversation_history,
                "stream": True,
                "keep_alive": -1,
                "options": {
                    "num_ctx": 1024,
                    "temperature": 0.6,
                    "num_predict": 28
                }
            }

            loop = asyncio.get_running_loop()
            
            # COLA ASÍNCRONA PRODUCER-CONSUMER CON IDIOMA Y VOZ NATIVOS
            tts_queue: asyncio.Queue = asyncio.Queue()

            async def tts_consumer_worker():
                while True:
                    item = await tts_queue.get()
                    if item is None:
                        tts_queue.task_done()
                        break
                    
                    sentence_text, voice, lang = item
                    if gen_id != current_generation_id or is_interrupted:
                        tts_queue.task_done()
                        break

                    audio_b64 = await loop.run_in_executor(
                        thread_pool, synthesize_audio_wav_base64, sentence_text, voice, lang
                    )

                    if audio_b64 and gen_id == current_generation_id and not is_interrupted:
                        await websocket.send_json({
                            "type": "audio_chunk",
                            "turn_id": turn_id,
                            "audio": audio_b64,
                            "text": sentence_text
                        })
                    tts_queue.task_done()

            tts_consumer_task = asyncio.create_task(tts_consumer_worker())

            try:
                def fetch_ollama_stream():
                    return requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=12)

                res = await loop.run_in_executor(thread_pool, fetch_ollama_stream)
                await websocket.send_json({"type": "status", "state": "speaking"})

                full_ai_response = []
                sentence_buffer = ""
                chunks_queued_count = 0

                for line in res.iter_lines():
                    if is_interrupted or gen_id != current_generation_id:
                        print("Generación cancelada por interrupción.")
                        break

                    if not line:
                        continue

                    chunk_data = json.loads(line.decode("utf-8") if isinstance(line, bytes) else line)
                    delta = chunk_data.get("message", {}).get("content", "")
                    if not delta:
                        continue

                    full_ai_response.append(delta)
                    sentence_buffer += delta
                    await websocket.send_json({
                        "type": "ai_chunk",
                        "turn_id": turn_id,
                        "delta": delta
                    })

                    words = sentence_buffer.strip().split()
                    
                    # DIVISIÓN CONTINUA FLUIDA (CHUNKING NATURAL):
                    # Priorizamos oraciones completas (. ! ? \n) y frases con sentido completo (>= 4 palabras).
                    # Evitamos cortar en comas tempranas como "Sí," o "You know," para que la voz no se frene.
                    has_sentence_end = any(p in sentence_buffer for p in [".", "!", "?", "\n"])
                    has_long_clause = any(p in sentence_buffer for p in [",", ";", ":"]) and len(words) >= 7

                    should_split = False
                    ready_sentence = ""

                    if has_sentence_end and len(words) >= 3:
                        parts = re.split(r'([.!?\n]+)', sentence_buffer)
                        if len(parts) > 1:
                            ready_sentence = (parts[0] + parts[1]).strip()
                            sentence_buffer = "".join(parts[2:])
                            should_split = True
                    elif has_long_clause:
                        parts = re.split(r'([,;:]+)', sentence_buffer)
                        # Solo cortar en la coma si antes de ella hay al menos 5 palabras completas
                        if len(parts) > 1 and len(parts[0].split()) >= 5:
                            ready_sentence = (parts[0] + parts[1]).strip()
                            sentence_buffer = "".join(parts[2:])
                            should_split = True
                        elif len(words) >= 11:
                            ready_sentence = " ".join(words[:8]).strip()
                            sentence_buffer = " ".join(words[8:]).strip()
                            should_split = True
                    elif len(words) >= 12:
                        ready_sentence = " ".join(words[:8]).strip()
                        sentence_buffer = " ".join(words[8:]).strip()
                        should_split = True

                    if should_split and ready_sentence and not is_interrupted and gen_id == current_generation_id:
                        is_es = (current_mode == "es") or is_text_spanish(ready_sentence)
                        chunk_voice = current_spanish_voice if is_es else current_english_voice
                        chunk_lang = "es" if is_es else "en-us"
                        chunks_queued_count += 1
                        await tts_queue.put((ready_sentence, chunk_voice, chunk_lang))

                if sentence_buffer.strip() and not is_interrupted and gen_id == current_generation_id:
                    ready_tail = sentence_buffer.strip()
                    is_es = (current_mode == "es") or is_text_spanish(ready_tail)
                    chunk_voice = current_spanish_voice if is_es else current_english_voice
                    chunk_lang = "es" if is_es else "en-us"
                    await tts_queue.put((ready_tail, chunk_voice, chunk_lang))

                # Señal de fin para el consumidor de TTS
                await tts_queue.put(None)
                await tts_consumer_task

                ai_text = "".join(full_ai_response).strip()
                if ai_text and not is_interrupted and gen_id == current_generation_id:
                    conversation_history.append({"role": "assistant", "content": ai_text})
                    await websocket.send_json({
                        "type": "ai_done",
                        "turn_id": turn_id,
                        "full_text": ai_text
                    })

                    # Solo si estamos en modo tutor de inglés ejecutamos traducción de apoyo y feedback
                    if current_mode == "en":
                        async def background_post_chat_analysis(t_id: str, u_text: str, a_text: str):
                            try:
                                analysis = await loop.run_in_executor(thread_pool, fast_analyze_turn, u_text, a_text)
                                if analysis and isinstance(analysis, dict):
                                    u_tr = analysis.get("user_tr")
                                    a_tr = analysis.get("ai_tr")
                                    tip = analysis.get("tip")
                                    if u_tr:
                                        await websocket.send_json({
                                            "type": "user_translation",
                                            "turn_id": t_id,
                                            "translation": u_tr
                                        })
                                    if a_tr:
                                        await websocket.send_json({
                                            "type": "ai_translation",
                                            "turn_id": t_id,
                                            "translation": a_tr
                                        })
                                    if tip and str(tip).strip().lower() not in ["null", "none", ""]:
                                        await websocket.send_json({
                                            "type": "coaching_feedback",
                                            "turn_id": t_id,
                                            "tip": tip
                                        })
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                print(f"Error en tarea de análisis: {e}")

                        cancel_background_analysis()
                        active_analysis_task = asyncio.create_task(
                            background_post_chat_analysis(turn_id, user_text, ai_text)
                        )

            except Exception as e:
                print(f"Error en streaming: {e}")
                await websocket.send_json({"type": "error", "message": f"Error: {e}"})

            await websocket.send_json({"type": "status", "state": "idle"})

    except WebSocketDisconnect:
        cancel_background_analysis()
        print("Cliente desconectado.")
    except Exception as e:
        cancel_background_analysis()
        print(f"Excepción WebSocket: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
