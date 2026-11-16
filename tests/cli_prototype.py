import os
import re
import sys
import time
import queue
import threading
import numpy as np
import requests
import sounddevice as sd
from colorama import init, Fore, Style
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro

# Inicializar colores en terminal Windows
init(autoreset=True)

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL_NAME = "qwen2.5:1.5b"  # Puedes cambiar a llama3.2:3b cuando lo descargues
SAMPLE_RATE = 16000
KOKORO_VOICE = "af_sarah"    # Voz natural en inglés femenino (af_sarah, af_bella, am_adam, am_michael)

SYSTEM_PROMPT = """You are an engaging, friendly native English speaker and conversation tutor.
Your mission is to help me practice my English speaking skills.
RULES:
1. Keep every response SHORT and conversational (1 to 2 sentences max).
2. Never give long lectures. Speak as if we are on a real-time phone call.
3. If I make a grammatical mistake, casually mention the correct way, then ask a simple follow-up question.
"""

def print_banner():
    print(Fore.CYAN + "=" * 70)
    print(Fore.GREEN + Style.BRIGHT + "   LOCAL ENGLISH PRACTICE AI ASSISTANT (100% Offline)")
    print(Fore.YELLOW + "   [Faster-Whisper CUDA] + [Ollama LLM] + [Kokoro-82M TTS]")
    print(Fore.CYAN + "=" * 70)

def record_audio_push_to_talk():
    """Graba audio desde el micrófono hasta que el usuario presiona Enter."""
    print(Fore.YELLOW + "\n[Micrófono Activo] Presiona ENTER para EMPEZAR a hablar...")
    input()
    
    audio_frames = []
    stop_event = threading.Event()
    
    def callback(indata, frames, time_info, status):
        if not stop_event.is_set():
            audio_frames.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', callback=callback)
    with stream:
        print(Fore.RED + Style.BRIGHT + ">>> GRABANDO... Habla ahora en inglés (Presiona ENTER para TERMINAR): ", end="", flush=True)
        input()
        stop_event.set()
        
    print(Fore.BLUE + "\n[Grabación finalizada. Procesando...]")
    if not audio_frames:
        return np.array([], dtype=np.float32)
        
    return np.concatenate(audio_frames, axis=0).flatten()

def translate_text(text: str) -> str:
    """Traduce texto al español de forma paralela usando Ollama."""
    if not text.strip():
        return ""
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": f"Translate the following English sentence to natural Spanish. Return ONLY the translation, no explanations, no quotes:\n{text}",
            "stream": False
        }
        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=10)
        if res.status_code == 200:
            return res.json().get("response", "").strip()
    except Exception as e:
        return f"(Traducción no disponible: {e})"
    return ""

class VoiceAssistant:
    def __init__(self):
        print(Fore.CYAN + "[1/3] Cargando Whisper en GPU (CUDA)...")
        self.stt_model = WhisperModel("base.en", device="cuda", compute_type="float16")
        
        print(Fore.CYAN + "[2/3] Cargando Kokoro TTS (ONNX)...")
        self.tts = Kokoro("models/kokoro-v0_19.onnx", "models/voices.bin")
        
        print(Fore.CYAN + "[3/3] Conectando con Ollama...")
        self.check_ollama()
        
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        print(Fore.GREEN + Style.BRIGHT + "\n✓ Todo listo para conversar.\n")

    def check_ollama(self):
        try:
            res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            models = [m["name"] for m in res.json().get("models", [])]
            print(Fore.GREEN + f"      Modelos disponibles en Ollama: {models}")
            if not any(MODEL_NAME in m for m in models):
                print(Fore.YELLOW + f"      [Aviso] Modelo {MODEL_NAME} no encontrado. Usando el primero disponible.")
        except Exception as e:
            print(Fore.RED + f"Error conectando con Ollama: {e}")

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio usando Faster-Whisper."""
        if len(audio_data) < SAMPLE_RATE * 0.3:
            return ""
            
        t0 = time.time()
        segments, _ = self.stt_model.transcribe(audio_data, language="en", beam_size=1)
        text = " ".join([segment.text for segment in segments]).strip()
        latency = round((time.time() - t0) * 1000)
        return text, latency

    def play_audio(self, text_chunk: str):
        """Genera y reproduce audio con Kokoro TTS."""
        text_clean = text_chunk.strip()
        if not text_clean:
            return
        try:
            samples, sr = self.tts.create(text_clean, voice=KOKORO_VOICE, speed=1.05)
            sd.play(samples, sr)
            sd.wait()
        except Exception as e:
            print(Fore.RED + f"\n[Error TTS]: {e}")

    def chat_turn(self, user_text: str):
        self.conversation_history.append({"role": "user", "content": user_text})
        
        # Iniciar traducción en segundo plano del usuario
        user_tr_thread = threading.Thread(target=lambda: None)
        user_translation_box = [""]
        def tr_user():
            user_translation_box[0] = translate_text(user_text)
        t_user = threading.Thread(target=tr_user)
        t_user.start()

        # Cola de audio para síntesis en streaming
        audio_queue = queue.Queue()
        playback_done = threading.Event()

        def audio_player_worker():
            while True:
                chunk = audio_queue.get()
                if chunk is None:
                    break
                self.play_audio(chunk)
                audio_queue.task_done()
            playback_done.set()

        player_thread = threading.Thread(target=audio_player_worker, daemon=True)
        player_thread.start()

        print(Fore.GREEN + Style.BRIGHT + "\n[AI Tutor]: ", end="", flush=True)
        
        full_ai_response = []
        sentence_buffer = ""
        first_token = True
        ttft = 0
        t_start = time.time()

        # Stream Ollama Chat
        payload = {
            "model": MODEL_NAME,
            "messages": self.conversation_history,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_predict": 120
            }
        }

        try:
            with requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=30) as r:
                for line in r.iter_lines():
                    if not line:
                        continue
                    data = requests.compat.json.loads(line)
                    delta = data.get("message", {}).get("content", "")
                    
                    if first_token and delta.strip():
                        ttft = round((time.time() - t_start) * 1000)
                        first_token = False
                        
                    print(Fore.GREEN + delta, end="", flush=True)
                    full_ai_response.append(delta)
                    sentence_buffer += delta

                    # Detección de fin de oración para enviar inmediatamente al TTS
                    if any(punct in delta for punct in [".", "!", "?", "\n"]):
                        parts = re.split(r'([.!?\n]+)', sentence_buffer)
                        if len(parts) > 1:
                            ready_sentence = parts[0] + parts[1]
                            audio_queue.put(ready_sentence)
                            sentence_buffer = "".join(parts[2:])

            if sentence_buffer.strip():
                audio_queue.put(sentence_buffer)

        except Exception as e:
            print(Fore.RED + f"\nError en streaming LLM: {e}")

        # Finalizar la cola de reproducción
        audio_queue.put(None)
        ai_text = "".join(full_ai_response).strip()
        self.conversation_history.append({"role": "assistant", "content": ai_text})

        # Traducir la respuesta de la IA en paralelo
        ai_translation = translate_text(ai_text)
        t_user.join()
        player_thread.join()

        # Visual Feed / Resumen visual de práctica
        print("\n" + Fore.LIGHTBLACK_EX + "-" * 70)
        print(Fore.CYAN + f"👤 Tú dijiste:      {user_text}")
        print(Fore.YELLOW + f"🇪🇸 Traducción:     {user_translation_box[0]}")
        print(Fore.GREEN + f"🤖 Tutor responde:  {ai_text}")
        print(Fore.YELLOW + f"🇪🇸 Traducción:     {ai_translation}")
        print(Fore.MAGENTA + f"⚡ Métricas:         Primer Token LLM: {ttft} ms")
        print(Fore.LIGHTBLACK_EX + "-" * 70)

def main():
    print_banner()
    try:
        assistant = VoiceAssistant()
    except Exception as e:
        print(Fore.RED + f"Fallo al iniciar el asistente: {e}")
        return

    print(Fore.WHITE + "Comandos especiales:")
    print("  - Presiona ENTER para hablar.")
    print("  - O escribe 't' y presiona ENTER para escribir texto manualmente si prefieres.")
    print("  - Escribe 'exit' para salir.\n")

    while True:
        try:
            choice = input(Fore.YELLOW + "\nPresiona [ENTER] para hablar, o escribe 't' para teclear ('exit' para salir): ").strip().lower()
            if choice == "exit":
                print(Fore.CYAN + "\n¡Hasta luego! Keep practicing your English! 👋")
                break
            
            if choice == "t":
                user_text = input(Fore.CYAN + "Escribe tu mensaje en inglés: ").strip()
                if not user_text:
                    continue
                assistant.chat_turn(user_text)
            else:
                audio = record_audio_push_to_talk()
                if len(audio) == 0:
                    print(Fore.RED + "No se detectó audio.")
                    continue
                
                print(Fore.BLUE + "[Transcribiendo con Faster-Whisper en GPU...]")
                transcription, latency = assistant.transcribe(audio)
                print(Fore.CYAN + f"Transcripción ({latency} ms): \"{transcription}\"")
                
                if not transcription.strip():
                    print(Fore.RED + "No se reconoció ninguna palabra. Inténtalo de nuevo.")
                    continue
                
                assistant.chat_turn(transcription)
                
        except KeyboardInterrupt:
            print(Fore.CYAN + "\n\nSesión terminada. Keep practicing! 👋")
            break

if __name__ == "__main__":
    main()

