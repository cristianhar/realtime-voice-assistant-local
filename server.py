import os
import sys
import time
import json
import base64
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Importación de arquitectura modular 'core'
import database
import tools
from core import (
    PROMPTS,
    MODEL_NAME,
    DEFAULT_SPANISH_VOICE,
    DEFAULT_ENGLISH_VOICE,
    is_text_spanish,
    SentenceChunker,
    load_stt_model,
    transcribe_audio_bytes,
    load_tts_model,
    synthesize_audio_wav_base64,
    fetch_ollama_chat_stream,
    fast_analyze_turn
)

stt_model = None
tts_model = None
thread_pool = ThreadPoolExecutor(max_workers=4)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global stt_model, tts_model
    database.init_db()
    print("=" * 60)
    print("Inicializando componentes modulares del Asistente de Voz...")
    stt_model = load_stt_model()
    tts_model = load_tts_model()
    print(f"✓ Modelo LLM configurado: {MODEL_NAME}")
    print("=" * 60)
    yield

app = FastAPI(title="Realtime Voice Assistant - Modular Architecture", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Endpoints REST y Archivos Estáticos
# -----------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("static/index.html")

@app.get("/api/history")
async def api_get_history():
    """Retorna mensajes recientes almacenados en SQLite."""
    return database.get_recent_messages(limit=30)

@app.get("/api/vocabulary")
async def api_get_vocabulary():
    """Retorna vocabulario y correcciones pedagógicas guardadas."""
    return database.get_vocabulary_list(limit=30)

@app.delete("/api/history")
async def api_clear_history():
    """Borra el historial y notas almacenadas en SQLite."""
    database.clear_all_history()
    return {"status": "ok", "message": "Historial limpiado exitosamente"}

@app.get("/api/notes")
async def api_get_notes():
    """Retorna notas de voz guardadas."""
    return database.get_recent_notes(limit=20)

@app.post("/api/notes")
async def api_save_note(note_data: dict):
    """Guarda una nota de voz."""
    content = note_data.get("content", "")
    title = note_data.get("title")
    if not content.strip():
        return {"status": "error", "message": "Contenido vacío"}
    note_id = database.save_voice_note(content, title)
    return {"status": "ok", "note_id": note_id}

@app.get("/api/profile")
async def api_get_profile():
    """Retorna el perfil y preferencias del usuario."""
    return database.get_user_profile()

@app.post("/api/profile")
async def api_set_profile(profile_data: dict):
    """Actualiza una propiedad en el perfil del usuario."""
    for k, v in profile_data.items():
        database.set_user_profile_value(k, str(v))
    return {"status": "ok", "profile": database.get_user_profile()}

# -----------------------------------------------------------------------------
# Orquestador WebSocket Full-Duplex en Tiempo Real
# -----------------------------------------------------------------------------
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✓ Cliente conectado al WebSocket.")

    current_mode = "en"
    current_spanish_voice = DEFAULT_SPANISH_VOICE
    current_english_voice = DEFAULT_ENGLISH_VOICE
    session_id = f"sess-{int(time.time())}"
    database.create_or_get_session(session_id, current_mode, current_english_voice)
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

            # 1. Configuración dinámica de modo de idioma
            if msg_type == "set_mode":
                cancel_background_analysis()
                new_mode = data.get("mode", "en")
                if new_mode in PROMPTS:
                    current_mode = new_mode
                    conversation_history = [{"role": "system", "content": PROMPTS[current_mode]}]
                    print(f"Modo cambiado a: {current_mode}")
                    await websocket.send_json({"type": "mode_changed", "mode": current_mode})
                continue

            # 2. Configuración dinámica de voces
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

            # 3. Interrupción instantánea (Barge-in)
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

            # 4. Transcripción parcial en vivo (Live Streaming STT)
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
                        thread_pool, transcribe_audio_bytes, stt_model, audio_bytes, current_mode
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

            # 5. Audio final del turno (activado por 650 ms de silencio en VAD)
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
                        thread_pool, transcribe_audio_bytes, stt_model, audio_bytes, current_mode
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

            # Enviar transcripción final al cliente
            await websocket.send_json({
                "type": "user_transcription",
                "turn_id": turn_id,
                "text": user_text,
                "stt_ms": stt_latency,
                "lang": detected_lang
            })

            # Persistir mensaje del usuario en SQLite
            database.save_message(
                session_id=session_id,
                role="user",
                content=user_text,
                turn_id=turn_id,
                stt_ms=stt_latency
            )

            current_generation_id += 1
            gen_id = current_generation_id
            is_interrupted = False
            loop = asyncio.get_running_loop()

            # -----------------------------------------------------------------
            # TOOL CALLING DIRECTO (Zero-Latency Local Tools: Hora, Notas, Vocabulario)
            # -----------------------------------------------------------------
            tool_result = tools.detect_and_execute_tool(user_text, current_mode)
            if tool_result:
                spoken_text = tool_result["spoken_response"]
                display_text = tool_result["display_response"]
                tool_name = tool_result["tool"]
                tool_lang = tool_result["lang"]
                print(f"🔧 Tool ejecutada: {tool_name} -> \"{spoken_text}\"")

                await websocket.send_json({
                    "type": "tool_executed",
                    "turn_id": turn_id,
                    "tool": tool_name,
                    "display_text": display_text,
                    "data": tool_result.get("data", {})
                })

                await websocket.send_json({"type": "status", "state": "speaking"})

                # Síntesis TTS directa ultra-rápida (TTFA ~200ms sin esperar al LLM)
                tool_voice = current_spanish_voice if tool_lang == "es" else current_english_voice
                audio_b64 = await loop.run_in_executor(
                    thread_pool, synthesize_audio_wav_base64, tts_model, spoken_text, tool_voice, tool_lang
                )

                if audio_b64 and not is_interrupted and gen_id == current_generation_id:
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "turn_id": turn_id,
                        "audio": audio_b64,
                        "text": spoken_text
                    })

                await websocket.send_json({
                    "type": "ai_done",
                    "turn_id": turn_id,
                    "full_text": display_text
                })

                database.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=display_text,
                    turn_id=turn_id
                )
                conversation_history.append({"role": "user", "content": user_text})
                conversation_history.append({"role": "assistant", "content": spoken_text})
                await websocket.send_json({"type": "status", "state": "idle"})
                continue

            # -----------------------------------------------------------------
            # TURNO CONVERSACIONAL CON LLM (Prioridad Absoluta de GPU)
            # -----------------------------------------------------------------
            conversation_history.append({"role": "user", "content": user_text})
            if len(conversation_history) > 9:
                conversation_history = [conversation_history[0]] + conversation_history[-8:]

            # Inyectar memoria persistente ultraligera (RAG híbrido de notas, perfil y FTS5)
            memory_block = database.get_smart_memory_context(user_text)
            current_system_prompt = PROMPTS[current_mode] + (f"\n{memory_block}" if memory_block else "")

            messages_for_llm = [{"role": "system", "content": current_system_prompt}] + [
                m for m in conversation_history if m.get("role") != "system"
            ]

            await websocket.send_json({"type": "status", "state": "thinking"})

            # Cola Asíncrona Producer-Consumer para Gapless TTS
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
                        thread_pool, synthesize_audio_wav_base64, tts_model, sentence_text, voice, lang
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
                res = await loop.run_in_executor(thread_pool, fetch_ollama_chat_stream, messages_for_llm)
                await websocket.send_json({"type": "status", "state": "speaking"})

                full_ai_response = []
                sentence_buffer = ""

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

                    # División continua de oraciones usando el SentenceChunker modular
                    ready_sentence, remaining, should_split = SentenceChunker.extract_ready_sentence(sentence_buffer)
                    if should_split and ready_sentence and not is_interrupted and gen_id == current_generation_id:
                        sentence_buffer = remaining
                        is_es = (current_mode == "es") or is_text_spanish(ready_sentence)
                        chunk_voice = current_spanish_voice if is_es else current_english_voice
                        chunk_lang = "es" if is_es else "en-us"
                        await tts_queue.put((ready_sentence, chunk_voice, chunk_lang))

                # Encolar remanente final de texto acumulado en el buffer
                if sentence_buffer.strip() and not is_interrupted and gen_id == current_generation_id:
                    ready_tail = sentence_buffer.strip()
                    is_es = (current_mode == "es") or is_text_spanish(ready_tail)
                    chunk_voice = current_spanish_voice if is_es else current_english_voice
                    chunk_lang = "es" if is_es else "en-us"
                    await tts_queue.put((ready_tail, chunk_voice, chunk_lang))

                # Señal de fin para el consumidor de audio
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

                    # Persistir en SQLite
                    database.save_message(
                        session_id=session_id,
                        role="assistant",
                        content=ai_text,
                        turn_id=turn_id
                    )

                    # Análisis pedagógico post-turno (solo modo inglés)
                    if current_mode == "en":
                        async def background_post_chat_analysis(t_id: str, u_text: str, a_text: str):
                            try:
                                analysis = await loop.run_in_executor(thread_pool, fast_analyze_turn, u_text, a_text)
                                if analysis and isinstance(analysis, dict):
                                    u_tr = analysis.get("user_tr")
                                    a_tr = analysis.get("ai_tr")
                                    tip = analysis.get("tip")
                                    if u_tr:
                                        database.update_message_translation(t_id, "user", u_tr)
                                        await websocket.send_json({
                                            "type": "user_translation",
                                            "turn_id": t_id,
                                            "translation": u_tr
                                        })
                                    if a_tr:
                                        database.update_message_translation(t_id, "assistant", a_tr)
                                        await websocket.send_json({
                                            "type": "ai_translation",
                                            "turn_id": t_id,
                                            "translation": a_tr
                                        })
                                    if tip and str(tip).strip().lower() not in ["null", "none", ""]:
                                        database.save_vocabulary_or_correction(
                                            phrase=u_text,
                                            tip=tip,
                                            language=current_mode
                                        )
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
