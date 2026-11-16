import io
import time
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from typing import Tuple

def load_stt_model() -> WhisperModel:
    """Carga Faster-Whisper en GPU CUDA fp16 con fallback seguro a CPU int8."""
    print("[STT] Inicializando Faster-Whisper Multilingüe...")
    try:
        model = WhisperModel("base", device="cuda", compute_type="float16")
        # Inferencia warm-up para inicializar kernels de CUDA
        list(model.transcribe(np.zeros(16000, dtype=np.float32), beam_size=1)[0])
        print("✓ Faster-Whisper activo en GPU CUDA (~26 ms)")
        return model
    except Exception as e:
        print(f"[STT] Fallback a CPU int8 por excepción: {e}")
        model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=4)
        print("✓ Faster-Whisper activo en CPU (int8)")
        return model

def transcribe_audio_bytes(stt_model: WhisperModel, audio_bytes: bytes, lang_mode: str = "auto") -> Tuple[str, int, str]:
    """
    Transcribe un flujo de bytes WAV (16kHz).
    Aplica filtro de energía acústica para ignorar suspiros, respiraciones o ruido de fondo.
    Retorna (texto_transcrito, latencia_ms, idioma_detectado).
    """
    t0 = time.time()
    try:
        data, sr = sf.read(io.BytesIO(audio_bytes))
        peak = float(np.max(np.abs(data)))
        rms = float(np.sqrt(np.mean(data**2)))

        # Filtro de respiración y ruido ambiental:
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
        text = " ".join([s.text for s in segments]).strip()
        latency_ms = round((time.time() - t0) * 1000)
        detected_lang = info.language if info else (lang_mode if lang_mode != "auto" else "en")
        print(f"-> STT ({latency_ms} ms) [{detected_lang}]: \"{text}\"")
        return text, latency_ms, detected_lang
    except Exception as e:
        print(f"Error en STT: {e}")
        return "", 0, "en"
