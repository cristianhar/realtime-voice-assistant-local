import unittest
import base64
import io
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import soundfile as sf
from core import (
    load_tts_model,
    synthesize_audio_wav_base64,
    load_stt_model,
    transcribe_audio_bytes,
    clean_tts_text
)

class TestLiveAudioModelsE2E(unittest.TestCase):
    """
    Prueba de audio real de circuito cerrado (Loopback Test):
    1. Carga Kokoro TTS ONNX (6 hilos).
    2. Sintetiza audio real en español con pronunciación nativa.
    3. Carga Faster-Whisper CUDA fp16.
    4. Transcribe el audio sintetizado y valida coincidencia fonética.
    """

    @classmethod
    def setUpClass(cls):
        print("\n[E2E Audio Loopback] Cargando modelos de audio en hardware local...")
        cls.tts = load_tts_model()
        cls.stt = load_stt_model()

    def test_tts_to_stt_loopback_spanish(self):
        phrase = "Hola, bienvenido al asistente de voz local."
        print(f"\n[1/2] Sintetizando con Kokoro (Dora - Español nativo): \"{phrase}\"")
        b64_wav = synthesize_audio_wav_base64(self.tts, phrase, voice_name="ef_dora", lang="es")
        self.assertTrue(len(b64_wav) > 1000)

        # Decodificar audio y comprobar duración
        audio_bytes = base64.b64decode(b64_wav)
        data, sr = sf.read(io.BytesIO(audio_bytes))
        duration_sec = len(data) / float(sr)
        print(f"  -> Duración generada: {duration_sec:.2f} s ({sr} Hz)")
        self.assertTrue(1.0 <= duration_sec <= 4.5)

        # Transcribir con Faster-Whisper CUDA
        print("[2/2] Transcribiendo audio sintetizado con Faster-Whisper CUDA...")
        transcription, latency_ms, detected_lang = transcribe_audio_bytes(self.stt, audio_bytes, lang_mode="es")
        print(f"  -> Transcripción obtenida ({latency_ms} ms) [{detected_lang}]: \"{transcription}\"")

        self.assertEqual(detected_lang, "es")
        self.assertIn("bienvenido", transcription.lower())
        self.assertIn("asistente", transcription.lower())

if __name__ == "__main__":
    unittest.main()
