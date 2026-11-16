"""
tts_kokoro_sanitizer.py - Text Sanitizer & Voice Blend Interpolator for Kokoro-82M
"""
import re
import numpy as np

def clean_for_tts(text: str) -> str:
    """
    Cleans raw LLM markdown outputs, removing symbols that cause TTS stuttering.
    """
    # 1. Strip URLs and file links
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    # 2. Strip code blocks and inline backticks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 3. Strip markdown symbols (*, _, #, >, ~)
    text = re.sub(r'[*_#~>]', '', text)
    # 4. Strip emojis and non-speech symbols
    text = re.sub(r'[^\w\s.,;:!?\'"áéíóúÁÉÍÓÚñÑüÜ¿¡-]', '', text)
    # 5. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def blend_voices(voice_a: np.ndarray, voice_b: np.ndarray, weight_a: float = 0.5) -> np.ndarray:
    """
    Interpolates two voice embeddings linearly.
    weight_a = 0.7 creates a voice with 70% features of A and 30% features of B.
    """
    weight_b = 1.0 - weight_a
    return (voice_a * weight_a) + (voice_b * weight_b)

if __name__ == "__main__":
    raw = "Hello! **Sure thing**, check this link: https://google.com `import math` *done*! 🚀"
    cleaned = clean_for_tts(raw)
    print("Raw:    ", raw)
    print("Cleaned:", cleaned)
