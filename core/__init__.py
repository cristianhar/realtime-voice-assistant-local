"""
Core package for the Realtime Local Voice Assistant.
Exports all modular components: audio, LLM streaming, chunking, database, tools, and configuration.
Uses lightweight lazy imports for heavy ML libraries (Kokoro, Faster-Whisper).
"""

from core.config import (
    PROMPTS,
    PERSONALITIES,
    DEFAULT_PERSONALITY,
    get_system_prompt,
    MODEL_NAME,
    OLLAMA_URL,
    DEFAULT_SPANISH_VOICE,
    DEFAULT_ENGLISH_VOICE,
    MODELS_DIR,
    STATIC_DIR,
    DB_PATH
)
from core.utils import is_text_spanish
from core.chunker import SentenceChunker
from core.llm import fetch_ollama_chat_stream, fast_analyze_turn
import database
import tools

def load_stt_model(*args, **kwargs):
    from core.stt import load_stt_model as _load
    return _load(*args, **kwargs)

def transcribe_audio_bytes(*args, **kwargs):
    from core.stt import transcribe_audio_bytes as _transcribe
    return _transcribe(*args, **kwargs)

def load_tts_model(*args, **kwargs):
    from core.tts import load_tts_model as _load
    return _load(*args, **kwargs)

def clean_tts_text(text: str) -> str:
    from core.tts import clean_tts_text as _clean
    return _clean(text)

def synthesize_audio_wav_base64(*args, **kwargs):
    from core.tts import synthesize_audio_wav_base64 as _synth
    return _synth(*args, **kwargs)

__all__ = [
    "PROMPTS",
    "PERSONALITIES",
    "DEFAULT_PERSONALITY",
    "get_system_prompt",
    "MODEL_NAME",
    "OLLAMA_URL",
    "DEFAULT_SPANISH_VOICE",
    "DEFAULT_ENGLISH_VOICE",
    "is_text_spanish",
    "SentenceChunker",
    "load_stt_model",
    "transcribe_audio_bytes",
    "load_tts_model",
    "clean_tts_text",
    "synthesize_audio_wav_base64",
    "fetch_ollama_chat_stream",
    "fast_analyze_turn",
    "database",
    "tools"
]
