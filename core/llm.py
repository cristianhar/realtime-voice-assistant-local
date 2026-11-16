import json
import requests
from typing import List, Dict, Any, Generator
from core.config import OLLAMA_URL, MODEL_NAME

def build_ollama_payload(messages: List[Dict[str, str]], stream: bool = True) -> Dict[str, Any]:
    """Genera el payload optimizado para inferencia rápida de Ollama en VRAM."""
    return {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": stream,
        "keep_alive": -1,  # Previene que Ollama descargue los pesos de VRAM
        "options": {
            "num_ctx": 1024,
            "temperature": 0.6,
            "num_predict": 28
        }
    }

def fetch_ollama_chat_stream(messages: List[Dict[str, str]], timeout: int = 12):
    """Realiza la petición streaming a Ollama /api/chat."""
    payload = build_ollama_payload(messages, stream=True)
    return requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=timeout)

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
