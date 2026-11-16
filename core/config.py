import os
import sys

# 1. Configuración de DLLs NVIDIA CUDA (cuBLAS) para Windows
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CUBLAS_BIN = os.path.join(PROJECT_ROOT, "venv", "Lib", "site-packages", "nvidia", "cublas", "bin")

def setup_cuda_dlls():
    """Registra los directorios de binarios cuBLAS en el PATH de Windows."""
    if os.path.isdir(CUBLAS_BIN):
        os.environ["PATH"] = CUBLAS_BIN + ";" + os.environ.get("PATH", "")
        try:
            os.add_dll_directory(CUBLAS_BIN)
        except Exception:
            pass

setup_cuda_dlls()

# 2. Rutas de Modelos y Datos
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
KOKORO_ONNX_PATH = os.path.join(MODELS_DIR, "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(MODELS_DIR, "voices-v1.0.bin")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
DB_PATH = os.path.join(PROJECT_ROOT, "voice_assistant.db")

# 3. Modelos y Endpoints
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

# 4. Configuración de Audio y Voces
DEFAULT_SPANISH_VOICE = "ef_dora"
DEFAULT_ENGLISH_VOICE = "af_sarah"
TTS_CPU_THREADS = 6
VAD_SILENCE_MS = 650
MAX_SPEECH_DURATION_MS = 7500

# 5. Prompts del Sistema Conversacional (Estilo Llamada Telefónica en Tiempo Real)
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

