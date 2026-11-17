import os
import sys
import time
import json
import base64
import asyncio
import threading
import urllib.request
import urllib.parse
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Importación de arquitectura modular 'core'
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
import database
import tools
from core import (
    PROMPTS,
    PERSONALITIES,
    DEFAULT_PERSONALITY,
    get_system_prompt,
    MODEL_NAME,
    OLLAMA_URL,
    DEFAULT_SPANISH_VOICE,
    DEFAULT_ENGLISH_VOICE,
    is_text_spanish,
    SentenceChunker,
    load_stt_model,
    transcribe_audio_bytes,
    load_tts_model,
    VOICE_BLENDS,
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
    print(f"[OK] Modelo LLM configurado: {MODEL_NAME}")

    # Verificación de salud y conectividad de Ollama
    try:
        import urllib.request
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                print(f"[OK] Ollama activo y respondiendo en {OLLAMA_URL}")
    except Exception:
        print(f"[AVISO] Ollama no respondió en {OLLAMA_URL}. Recuerda iniciar 'ollama serve' o 'ollama run {MODEL_NAME}'.")

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

@app.get("/api/gpu-status")
async def api_get_gpu_status():
    """Retorna telemetría en tiempo real de la GPU NVIDIA (temperatura, VRAM, estado)."""
    return tools.query_gpu_status()

@app.get("/api/notes")
async def api_get_notes(limit: int = 50):
    """Retorna notas de voz guardadas."""
    return database.get_recent_notes(limit=limit)

@app.post("/api/notes")
async def api_save_note(note_data: dict):
    """Guarda una nota de voz."""
    content = note_data.get("content", "")
    title = note_data.get("title")
    if not content.strip():
        return {"status": "error", "message": "Contenido vacío"}
    note_id = database.save_voice_note(content, title)
    return {"status": "ok", "note_id": note_id}

@app.delete("/api/notes/{note_id}")
async def api_delete_note(note_id: int):
    """Elimina una nota de voz por ID."""
    success = database.delete_voice_note(note_id)
    return {"status": "ok" if success else "not_found", "deleted": success}

@app.post("/api/notes/synthesize")
def api_synthesize_notes():
    """Sintetiza de forma ejecutiva todas las notas recientes usando Llama 3.2."""
    notes = database.get_recent_notes(limit=25)
    if not notes:
        return {"status": "empty", "summary": "No tienes notas guardadas para sintetizar todavía."}
    
    bullets = "\n".join([f"• [{n['title']}]: {n['content']}" for n in notes])
    prompt = f"Eres un asistente ejecutivo. Analiza y sintetiza en 3 o 4 viñetas accionables, claras y concisas las siguientes notas de voz del usuario:\n\n{bullets}\n\nConcluye con un breve mensaje motivador de 1 frase."
    
    try:
        ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        data = json.dumps({
            "model": "llama3.2:3b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": -1
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{ollama_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            summary = body.get("message", {}).get("content", "").strip()
            if summary:
                return {"status": "ok", "summary": summary, "count": len(notes)}
    except Exception as e:
        print(f"[Notes Synthesis Warning] Ollama no disponible: {e}")
    
    # Fallback local ejecutivo estructurado si Ollama no responde de inmediato
    bullets_summary = "\n".join([f"• [{n['title']}]: {n['content']}" for n in notes[:6]])
    fallback_summary = f"Síntesis de tus {len(notes)} notas recientes:\n\n{bullets_summary}\n\n💡 Recuerda revisar tus pendientes clave hoy."
    return {"status": "ok", "summary": fallback_summary, "count": len(notes)}

# ==============================================================================
# GESTIÓN DE HISTORIAL DE CONVERSACIONES (ESTILO CHATGPT)
# ==============================================================================

@app.get("/api/sessions")
def api_get_sessions(limit: int = 50):
    """Retorna la lista de conversaciones recientes guardadas en SQLite."""
    sessions = database.get_all_sessions(limit=limit)
    return {"status": "ok", "sessions": sessions, "count": len(sessions)}

@app.post("/api/sessions")
def api_create_session(data: Optional[Dict[str, Any]] = None):
    """Crea una nueva conversación vacía."""
    payload = data or {}
    mode = payload.get("mode", "en")
    voice = payload.get("voice", DEFAULT_ENGLISH_VOICE)
    title = payload.get("title", "Nueva conversación")
    session_id = f"sess-{int(time.time() * 1000)}"
    database.create_or_get_session(session_id, mode, voice, title=title)
    return {"status": "ok", "session_id": session_id, "title": title}

@app.get("/api/sessions/{session_id}/messages")
def api_get_session_messages(session_id: str):
    """Retorna todos los mensajes de una conversación específica."""
    msgs = database.get_session_messages(session_id)
    return {"status": "ok", "session_id": session_id, "messages": msgs, "count": len(msgs)}

@app.put("/api/sessions/{session_id}/title")
@app.patch("/api/sessions/{session_id}/title")
def api_update_session_title(session_id: str, data: Dict[str, Any]):
    """Actualiza el nombre/título de una conversación."""
    title = data.get("title", "").strip()
    if not title:
        return {"status": "error", "message": "El título no puede estar vacío"}
    success = database.update_session_title(session_id, title)
    return {"status": "ok" if success else "not_found", "title": title, "session_id": session_id}

@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str):
    """Elimina una conversación y sus mensajes de SQLite."""
    success = database.delete_session(session_id)
    return {"status": "ok" if success else "not_found", "deleted": success, "session_id": session_id}

@app.post("/api/sessions/{session_id}/generate-title")
def api_generate_session_title(session_id: str):
    """Genera un título inteligente con LLaMA 3.2 basado en el contenido de la conversación."""
    title = database.generate_ai_session_title(session_id)
    return {"status": "ok", "session_id": session_id, "title": title}

@app.get("/api/personalities")
async def api_get_personalities():
    """Retorna las personalidades conversacionales disponibles."""
    return PERSONALITIES

@app.get("/api/personas")
async def api_get_personas():
    """Retorna las personas avanzadas cargadas dinámicamente desde personas/."""
    personas_dir = os.path.join(os.path.dirname(__file__), "personas")
    result = []
    if os.path.isdir(personas_dir):
        for fname in os.listdir(personas_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(personas_dir, fname), "r", encoding="utf-8") as f:
                        result.append(json.load(f))
                except Exception:
                    pass
    return result

@app.get("/api/plugins")
async def api_get_plugins():
    """Retorna el catálogo de herramientas y plugins modulares activos."""
    try:
        from core.plugin_loader import get_loaded_tools_metadata
        return get_loaded_tools_metadata()
    except Exception:
        return []

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
    print("[OK] Cliente conectado al WebSocket.")

    current_mode = "en"
    current_personality = DEFAULT_PERSONALITY
    current_spanish_voice = DEFAULT_SPANISH_VOICE
    current_english_voice = DEFAULT_ENGLISH_VOICE
    is_whisper_mode = False
    session_id = f"sess-{int(time.time() * 1000)}"
    # Lazy Session Creation: No persistir en SQLite hasta que el usuario envíe su primer mensaje
    conversation_history: List[Dict[str, str]] = [
        {"role": "system", "content": get_system_prompt(current_mode, current_personality)}
    ]

    current_generation_id = 0
    is_interrupted = False
    active_analysis_task: Optional[asyncio.Task] = None
    active_turn_task: Optional[asyncio.Task] = None
    active_stream_response = None
    active_cancel_event: Optional[threading.Event] = None
    stt_busy = False
    ws_send_lock = asyncio.Lock()

    async def safe_send_json(payload: dict):
        """Envío thread-safe / coroutine-safe garantizado sobre el WebSocket."""
        try:
            async with ws_send_lock:
                await websocket.send_json(payload)
        except Exception:
            pass

    def cancel_background_analysis():
        nonlocal active_analysis_task
        if active_analysis_task and not active_analysis_task.done():
            active_analysis_task.cancel()
            active_analysis_task = None

    def cancel_active_turn():
        """
        Barge-in instantáneo (<10ms):
        1. Invalida generation_id y marca is_interrupted.
        2. Cierra inmediatamente el socket HTTP de streaming con Ollama (abort en caliente).
        3. Detiene el hilo de lectura del stream.
        4. Cancela la tarea asyncio de generación y síntesis de audio TTS en curso.
        """
        nonlocal active_turn_task, active_stream_response, active_cancel_event, is_interrupted, current_generation_id
        is_interrupted = True
        current_generation_id += 1
        cancel_background_analysis()

        if active_cancel_event:
            try:
                active_cancel_event.set()
            except Exception:
                pass

        if active_stream_response:
            try:
                active_stream_response.close()
            except Exception:
                pass

        if active_turn_task and not active_turn_task.done():
            active_turn_task.cancel()

        active_turn_task = None
        active_stream_response = None
        active_cancel_event = None

    async def maybe_auto_title_session(sid: str):
        try:
            sess_info = database.get_session_by_id(sid)
            if sess_info and (not sess_info.get("title") or sess_info.get("title") == "Nueva conversación"):
                msgs = database.get_session_messages(sid)
                if len(msgs) >= 2:
                    loop = asyncio.get_event_loop()
                    new_title = await loop.run_in_executor(None, database.generate_ai_session_title, sid)
                    if new_title and new_title != "Nueva conversación":
                        await safe_send_json({
                            "type": "title_generated",
                            "session_id": sid,
                            "title": new_title
                        })
        except Exception as e:
            print(f"[AutoTitling Error] {e}")

    async def execute_turn_pipeline(u_text: str, t_id: str, gen_id: int, det_lang: str, stt_ms: int):
        """
        Pipeline desacoplado no bloqueante para el turno de la IA:
        Permite que el loop principal siga escuchando el WebSocket en todo momento (Full-Duplex / Barge-in).
        """
        nonlocal is_whisper_mode, conversation_history, active_stream_response, active_cancel_event, active_analysis_task
        loop = asyncio.get_running_loop()
        spoken_sentences: List[str] = []
        full_ai_response: List[str] = []
        res = None
        cancel_event = None
        tts_consumer_task: Optional[asyncio.Task] = None

        try:
            # 1. Enviar transcripción final confirmada del usuario
            await safe_send_json({
                "type": "user_transcription",
                "turn_id": t_id,
                "text": u_text,
                "stt_ms": stt_ms,
                "lang": det_lang
            })

            # 2. Persistir mensaje del usuario en SQLite (Lazy session creation)
            database.create_or_get_session(session_id, current_mode, current_english_voice)
            database.save_message(
                session_id=session_id,
                role="user",
                content=u_text,
                turn_id=t_id,
                stt_ms=stt_ms
            )

            # 3. Detección automática de intención de Modo Susurro
            whisper_on_triggers = ["susurra", "modo susurro", "habla suave", "habla bajito", "whisper", "night mode", "modo noche", "tono suave"]
            whisper_off_triggers = ["voz normal", "desactiva susurro", "normal voice", "disable whisper", "habla fuerte", "apaga susurro"]
            user_lower = u_text.lower()
            if any(wt in user_lower for wt in whisper_on_triggers) and not is_whisper_mode:
                is_whisper_mode = True
                await safe_send_json({"type": "whisper_mode_changed", "enabled": True})
            elif any(wt in user_lower for wt in whisper_off_triggers) and is_whisper_mode:
                is_whisper_mode = False
                await safe_send_json({"type": "whisper_mode_changed", "enabled": False})

            if is_interrupted or gen_id != current_generation_id:
                return

            # -----------------------------------------------------------------
            # 4. TOOL CALLING DIRECTO (Zero-Latency Local Tools: Hora, Notas, Vocabulario)
            # -----------------------------------------------------------------
            tool_result = tools.detect_and_execute_tool(u_text, current_mode)
            if tool_result:
                spoken_text = tool_result["spoken_response"]
                display_text = tool_result["display_response"]
                tool_name = tool_result["tool"]
                tool_lang = tool_result["lang"]
                print(f"🔧 Tool ejecutada: {tool_name} -> \"{spoken_text}\"")

                await safe_send_json({
                    "type": "tool_executed",
                    "turn_id": t_id,
                    "tool": tool_name,
                    "display_text": display_text,
                    "display_response": display_text,
                    "spoken_response": spoken_text,
                    "data": tool_result.get("data", {})
                })

                await safe_send_json({"type": "status", "state": "speaking"})

                # Síntesis TTS directa ultra-rápida (TTFA ~200ms sin esperar al LLM)
                tool_voice = current_spanish_voice if tool_lang == "es" else current_english_voice
                audio_b64 = await loop.run_in_executor(
                    thread_pool, synthesize_audio_wav_base64, tts_model, spoken_text, tool_voice, tool_lang, is_whisper_mode
                )

                if audio_b64 and not is_interrupted and gen_id == current_generation_id:
                    await safe_send_json({
                        "type": "audio_chunk",
                        "turn_id": t_id,
                        "audio": audio_b64,
                        "text": spoken_text
                    })

                await safe_send_json({
                    "type": "ai_chunk",
                    "turn_id": t_id,
                    "delta": spoken_text
                })

                await safe_send_json({
                    "type": "ai_done",
                    "turn_id": t_id,
                    "full_text": display_text or spoken_text
                })

                database.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=display_text,
                    turn_id=t_id
                )
                asyncio.create_task(maybe_auto_title_session(session_id))
                conversation_history.append({"role": "user", "content": u_text})
                conversation_history.append({"role": "assistant", "content": spoken_text})
                await safe_send_json({"type": "status", "state": "idle"})
                return

            # -----------------------------------------------------------------
            # 5. TURNO CONVERSACIONAL CON LLM (Prioridad Absoluta de GPU)
            # -----------------------------------------------------------------
            conversation_history.append({"role": "user", "content": u_text})
            # Mantener hasta 30 mensajes recientes (15 turnos completos) en el contexto de LLaMA 3.2
            if len(conversation_history) > 31:
                conversation_history = [conversation_history[0]] + conversation_history[-30:]

            # Inyectar memoria persistente ultraligera (RAG híbrido de notas, perfil y FTS5)
            memory_block = database.get_smart_memory_context(u_text)
            whisper_prompt = "\n[INSTRUCCIÓN MODO SUSURRO: Responde con tono íntimo, muy suave, relajante y oraciones concisas y tranquilas.]" if is_whisper_mode else ""
            current_system_prompt = get_system_prompt(current_mode, current_personality) + whisper_prompt + (f"\n{memory_block}" if memory_block else "")

            messages_for_llm = [{"role": "system", "content": current_system_prompt}] + [
                m for m in conversation_history if m.get("role") != "system"
            ]

            await safe_send_json({"type": "status", "state": "thinking"})

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
                        thread_pool, synthesize_audio_wav_base64, tts_model, sentence_text, voice, lang, is_whisper_mode
                    )

                    if audio_b64 and gen_id == current_generation_id and not is_interrupted:
                        spoken_sentences.append(sentence_text)
                        await safe_send_json({
                            "type": "audio_chunk",
                            "turn_id": t_id,
                            "audio": audio_b64,
                            "text": sentence_text
                        })
                    tts_queue.task_done()

            tts_consumer_task = asyncio.create_task(tts_consumer_worker())

            # Solicitud HTTP de streaming al LLM
            res = await loop.run_in_executor(thread_pool, fetch_ollama_chat_stream, messages_for_llm)
            active_stream_response = res
            cancel_event = threading.Event()
            active_cancel_event = cancel_event

            line_queue: asyncio.Queue = asyncio.Queue()

            def ollama_stream_reader(stream_resp, out_queue, ev_loop, cancel_ev):
                try:
                    for line in stream_resp.iter_lines():
                        if cancel_ev.is_set():
                            break
                        if line:
                            ev_loop.call_soon_threadsafe(out_queue.put_nowait, line)
                except Exception:
                    pass
                finally:
                    try:
                        stream_resp.close()
                    except Exception:
                        pass
                    ev_loop.call_soon_threadsafe(out_queue.put_nowait, None)

            reader_thread = threading.Thread(
                target=ollama_stream_reader,
                args=(res, line_queue, loop, cancel_event),
                daemon=True
            )
            reader_thread.start()

            await safe_send_json({"type": "status", "state": "speaking"})

            sentence_buffer = ""
            chunks_sent = 0

            while True:
                line = await line_queue.get()
                if line is None:
                    break
                if is_interrupted or gen_id != current_generation_id:
                    cancel_event.set()
                    if res:
                        try:
                            res.close()
                        except Exception:
                            pass
                    break

                chunk_data = json.loads(line.decode("utf-8") if isinstance(line, bytes) else line)
                delta = chunk_data.get("message", {}).get("content", "")
                if not delta:
                    continue

                full_ai_response.append(delta)
                sentence_buffer += delta
                await safe_send_json({
                    "type": "ai_chunk",
                    "turn_id": t_id,
                    "delta": delta
                })

                # División continua de oraciones usando el SentenceChunker modular
                is_first = (chunks_sent == 0)
                ready_sentence, remaining, should_split = SentenceChunker.extract_ready_sentence(sentence_buffer, is_first_chunk=is_first)
                if should_split and ready_sentence and not is_interrupted and gen_id == current_generation_id:
                    chunks_sent += 1
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
            if tts_consumer_task:
                await tts_consumer_task

            ai_text = "".join(full_ai_response).strip()
            if is_interrupted or gen_id != current_generation_id:
                # Interrumpido durante la respuesta: truncar contexto a lo que el usuario realmente escuchó
                spoken_part = " ".join(spoken_sentences).strip()
                if spoken_part:
                    interrupted_summary = f"{spoken_part} ... [interrumpido]"
                    conversation_history.append({"role": "assistant", "content": interrupted_summary})
                    database.save_message(
                        session_id=session_id,
                        role="assistant",
                        content=interrupted_summary,
                        turn_id=t_id
                    )
                    await safe_send_json({
                        "type": "ai_interrupted",
                        "turn_id": t_id,
                        "partial_text": interrupted_summary
                    })
            else:
                # Turno completado con éxito
                if ai_text:
                    conversation_history.append({"role": "assistant", "content": ai_text})
                    await safe_send_json({
                        "type": "ai_done",
                        "turn_id": t_id,
                        "full_text": ai_text
                    })

                    database.save_message(
                        session_id=session_id,
                        role="assistant",
                        content=ai_text,
                        turn_id=t_id
                    )
                    asyncio.create_task(maybe_auto_title_session(session_id))

                    # Análisis pedagógico post-turno (solo modo inglés)
                    if current_mode == "en":
                        async def background_post_chat_analysis(tid: str, user_msg: str, ai_msg: str):
                            try:
                                analysis = await loop.run_in_executor(thread_pool, fast_analyze_turn, user_msg, ai_msg)
                                if analysis and isinstance(analysis, dict):
                                    u_tr = analysis.get("user_tr")
                                    a_tr = analysis.get("ai_tr")
                                    tip = analysis.get("tip")
                                    if u_tr:
                                        database.update_message_translation(tid, "user", u_tr)
                                        await safe_send_json({
                                            "type": "user_translation",
                                            "turn_id": tid,
                                            "translation": u_tr
                                        })
                                    if a_tr:
                                        database.update_message_translation(tid, "assistant", a_tr)
                                        await safe_send_json({
                                            "type": "ai_translation",
                                            "turn_id": tid,
                                            "translation": a_tr
                                        })
                                    if tip and str(tip).strip().lower() not in ["null", "none", ""]:
                                        database.save_vocabulary_or_correction(
                                            phrase=user_msg,
                                            tip=tip,
                                            language=current_mode
                                        )
                                        await safe_send_json({
                                            "type": "coaching_feedback",
                                            "turn_id": tid,
                                            "tip": tip
                                        })
                            except asyncio.CancelledError:
                                pass
                            except Exception as ex:
                                print(f"Error en tarea de análisis: {ex}")

                        cancel_background_analysis()
                        active_analysis_task = asyncio.create_task(
                            background_post_chat_analysis(t_id, u_text, ai_text)
                        )

        except asyncio.CancelledError:
            # Captura de cancelación instantánea (<1ms) activada por cancel_active_turn()
            if cancel_event:
                try:
                    cancel_event.set()
                except Exception:
                    pass
            if res:
                try:
                    res.close()
                except Exception:
                    pass
            if tts_consumer_task and not tts_consumer_task.done():
                tts_consumer_task.cancel()

            spoken_part = " ".join(spoken_sentences).strip()
            if spoken_part:
                interrupted_summary = f"{spoken_part} ... [interrumpido]"
                conversation_history.append({"role": "assistant", "content": interrupted_summary})
                database.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=interrupted_summary,
                    turn_id=t_id
                )
                await safe_send_json({
                    "type": "ai_interrupted",
                    "turn_id": t_id,
                    "partial_text": interrupted_summary
                })
        except Exception as e:
            print(f"Error en streaming / ejecución de turno: {e}")
            await safe_send_json({"type": "error", "message": f"Error: {e}"})
        finally:
            active_stream_response = None
            active_cancel_event = None
            if not is_interrupted and gen_id == current_generation_id:
                await safe_send_json({"type": "status", "state": "idle"})

    try:
        # Loop principal de WebSocket 100% NO BLOQUEANTE:
        # Recibe señales de Barge-in (interrupt) y audio de forma instantánea en cualquier milisegundo.
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            # 0. Cambio de sesión conversacional (Historial estilo ChatGPT)
            if msg_type == "switch_session":
                cancel_active_turn()
                target_session_id = data.get("session_id")
                if target_session_id:
                    session_id = target_session_id
                    current_sess = database.get_session_by_id(session_id)
                    if current_sess:
                        prev_messages = database.get_session_messages(session_id)
                        curr_title = current_sess.get("title") or "Nueva conversación"
                    else:
                        prev_messages = []
                        curr_title = "Nueva conversación"

                    conversation_history = [{"role": "system", "content": get_system_prompt(current_mode, current_personality)}]
                    for pm in prev_messages[-30:]:
                        conversation_history.append({"role": pm["role"], "content": pm["content"]})
                    print(f"Sesión activa cambiada a: {session_id} ('{curr_title}')")
                    await safe_send_json({
                        "type": "session_switched",
                        "session_id": session_id,
                        "title": curr_title,
                        "messages_count": len(prev_messages)
                    })
                continue

            # 1. Configuración dinámica de modo de idioma
            if msg_type == "set_mode":
                cancel_active_turn()
                new_mode = data.get("mode", "en")
                if new_mode in ["en", "es", "auto"]:
                    current_mode = new_mode
                    sys_msg = {"role": "system", "content": get_system_prompt(current_mode, current_personality)}
                    if conversation_history and conversation_history[0].get("role") == "system":
                        conversation_history[0] = sys_msg
                    else:
                        conversation_history.insert(0, sys_msg)
                    print(f"Modo cambiado a: {current_mode} (personalidad: {current_personality})")
                    await safe_send_json({"type": "mode_changed", "mode": current_mode})
                continue

            # 2. Configuración dinámica de personalidad conversacional
            if msg_type == "set_personality":
                cancel_active_turn()
                new_personality = data.get("personality", DEFAULT_PERSONALITY)
                if new_personality in PERSONALITIES:
                    current_personality = new_personality
                    sys_msg = {"role": "system", "content": get_system_prompt(current_mode, current_personality)}
                    if conversation_history and conversation_history[0].get("role") == "system":
                        conversation_history[0] = sys_msg
                    else:
                        conversation_history.insert(0, sys_msg)
                    print(f"Personalidad cambiada a: {current_personality}")
                    await safe_send_json({"type": "personality_changed", "personality": current_personality})
                continue

            # Configuración dinámica de Modo Susurro (Whisper Mode)
            if msg_type == "set_whisper_mode":
                is_whisper_mode = bool(data.get("enabled", False))
                print(f"Modo Susurro: {'ACTIVADO' if is_whisper_mode else 'DESACTIVADO'}")
                await safe_send_json({"type": "whisper_mode_changed", "enabled": is_whisper_mode})
                continue

            # Configuración dinámica de voces
            if msg_type == "set_voice":
                new_voice = data.get("voice", "")
                if new_voice:
                    if new_voice in VOICE_BLENDS or "blend" in new_voice:
                        current_spanish_voice = new_voice
                        current_english_voice = new_voice
                    elif new_voice.startswith("e"):
                        current_spanish_voice = new_voice
                    else:
                        current_english_voice = new_voice
                    print(f"Voz configurada -> ES: {current_spanish_voice}, EN: {current_english_voice}")
                    await safe_send_json({
                        "type": "voice_changed",
                        "spanish_voice": current_spanish_voice,
                        "english_voice": current_english_voice
                    })
                continue

            # 3. Interrupción instantánea (Barge-in / Speech Start)
            if msg_type == "interrupt":
                print("⚡ Interrupción recibida del cliente (Barge-in).")
                cancel_active_turn()
                await safe_send_json({"type": "interrupted"})
                await safe_send_json({"type": "status", "state": "idle"})
                continue

            # 4. Transcripción parcial en vivo (Live Streaming STT)
            if msg_type == "audio_partial":
                if stt_busy:
                    continue
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
                        await safe_send_json({
                            "type": "user_partial_transcription",
                            "text": partial_text,
                            "lang": detected_lang
                        })
                finally:
                    stt_busy = False
                continue

            # 5. Entrada del usuario (audio o texto)
            user_text = ""
            stt_latency = 0
            detected_lang = "en"
            turn_id = data.get("turn_id") or f"turn-{int(time.time() * 1000)}"

            if msg_type in ["audio", "audio_final"]:
                # Si el usuario envió nuevo audio final, cancelar cualquier turno previo en curso
                cancel_active_turn()
                is_interrupted = False

                audio_base64 = data.get("audio", "")
                if not audio_base64:
                    continue
                audio_bytes = base64.b64decode(audio_base64)
                await safe_send_json({"type": "status", "state": "transcribing"})

                loop = asyncio.get_running_loop()
                try:
                    stt_busy = True
                    user_text, stt_latency, detected_lang = await loop.run_in_executor(
                        thread_pool, transcribe_audio_bytes, stt_model, audio_bytes, current_mode
                    )
                finally:
                    stt_busy = False

                if not user_text:
                    await safe_send_json({"type": "status", "state": "idle"})
                    continue

            elif msg_type == "text":
                cancel_active_turn()
                is_interrupted = False
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue
                detected_lang = "es" if is_text_spanish(user_text) else "en"
            else:
                continue

            # Iniciar pipeline de respuesta de la IA en segundo plano de forma no bloqueante
            current_generation_id += 1
            gen_id = current_generation_id
            active_turn_task = asyncio.create_task(
                execute_turn_pipeline(user_text, turn_id, gen_id, detected_lang, stt_latency)
            )

    except WebSocketDisconnect:
        cancel_active_turn()
        print("Cliente desconectado.")
    except Exception as e:
        cancel_active_turn()
        print(f"Excepción WebSocket: {e}")

def get_local_ip() -> str:
    """Detecta la dirección IP de la máquina en la red local Wi-Fi o Ethernet."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def ensure_ssl_certificates(local_ip: str) -> tuple:
    """Genera certificados autofirmados X.509 válidos para HTTPS y Web Audio en móviles."""
    certs_dir = os.path.join(PROJECT_ROOT, "certs")
    os.makedirs(certs_dir, exist_ok=True)
    cert_path = os.path.join(certs_dir, "cert.pem")
    key_path = os.path.join(certs_dir, "key.pem")

    if not (os.path.isfile(cert_path) and os.path.isfile(key_path)):
        try:
            import datetime
            import ipaddress
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "VoiceAssistantLocal"),
            ])
            san_items = [
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))
            ]
            if local_ip != "127.0.0.1":
                san_items.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))

            now = datetime.datetime.now(datetime.timezone.utc)
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                now - datetime.timedelta(days=1)
            ).not_valid_after(
                now + datetime.timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName(san_items), critical=False
            ).sign(key, hashes.SHA256())

            with open(key_path, "wb") as f:
                f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            print("[OK] Certificados SSL generados exitosamente en certs/")
        except Exception as e:
            print(f"[AVISO] No se pudieron generar certificados SSL: {e}")
            return None, None

    return cert_path, key_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Realtime Local Voice Assistant Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP para escuchar (0.0.0.0 para red local)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor (8000)")
    parser.add_argument("--https", action="store_true", help="Activar HTTPS para micrófono en móviles (iOS/Android)")
    args = parser.parse_args()

    local_ip = get_local_ip()
    port = args.port

    ssl_keyfile = None
    ssl_certfile = None
    protocol = "http"

    if args.https or os.environ.get("USE_HTTPS") == "1":
        cert_p, key_p = ensure_ssl_certificates(local_ip)
        if cert_p and key_p:
            ssl_certfile = cert_p
            ssl_keyfile = key_p
            protocol = "https"

    print("\n" + "=" * 65)
    print("  🎙️ VOICE ASSISTANT LOCAL - SERVIDOR MULTI-DISPOSITIVO")
    print("=" * 65)
    print(f"  💻 En esta PC:     {protocol}://localhost:{port}")
    print(f"  📱 En tu Celular:  {protocol}://{local_ip}:{port}")
    if protocol == "https":
        print("  🔒 Modo HTTPS activo: habilita micrófono en Chrome y Safari móvil.")
        print("     * Acepta la advertencia de certificado autofirmado en tu celular.")
    else:
        print("  💡 Acceso móvil con micrófono:")
        print(f"     Opción A (Recomendada): Inicia con HTTPS: python server.py --https")
        print(f"     Opción B (Android Chrome): chrome://flags/#unsafely-treat-insecure-origin-as-secure -> {protocol}://{local_ip}:{port}")
    print("=" * 65 + "\n")

    uvicorn.run(
        app,
        host=args.host,
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        reload=False
    )
