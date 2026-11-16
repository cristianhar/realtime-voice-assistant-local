"""
generate_humanized_demo_audio.py - Synthesizes real comparison audio:
1. Without Humanizer: Dead digital silence into abrupt speech.
2. With Humanizer: Natural micro-inhalation pre-speech breath into speech.
"""
import os
import sys
import wave
import numpy as np
import soundfile as sf

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.tts import load_tts_model, clean_tts_text

def create_demo_audios():
    print("[1/4] Cargando modelo Kokoro-82M ONNX...")
    tts_model = load_tts_model()

    text_phrase = "Hola Cristian, claro que sí. Ya estoy activo con la micro respiración humana y listo para conversar."
    print(f"[2/4] Sintetizando locución: '{text_phrase}'...")

    # Sintetizar locución base a 24kHz
    target_voice = "ef_dora"
    samples, sr = tts_model.create(
        clean_tts_text(text_phrase),
        voice=target_voice,
        speed=1.05,
        lang="es",
        sentence_pause=0.2,
        clause_pause=0.1
    )

    out_dir = os.path.join("static", "audio")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Versión SIN humanizador (empieza de 50ms de silencio digital absoluto)
    silence_lead = np.zeros(int(sr * 0.05), dtype=np.float32)
    audio_without = np.concatenate([silence_lead, samples])
    path_without = os.path.join(out_dir, "demo_without_humanizer.wav")
    sf.write(path_without, audio_without, sr)
    print(f"[3/4] Guardado audio SIN humanizador: {path_without}")

    # 2. Versión CON humanizador (micro-inhalación sutil + speech)
    breath_path = os.path.join(out_dir, "breath_subtle.wav")
    with wave.open(breath_path, "r") as wf:
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        breath_samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    # Respiro sutil con volumen calibrado (~ -18dB)
    breath_samples = breath_samples * 0.85
    # Breve pausa natural de 20ms entre el fin de la toma de aire y el inicio del primer fonema
    gap = np.zeros(int(sr * 0.02), dtype=np.float32)

    audio_with = np.concatenate([breath_samples, gap, samples])
    path_with = os.path.join(out_dir, "demo_with_humanizer.wav")
    sf.write(path_with, audio_with, sr)
    print(f"[4/4] Guardado audio CON humanizador: {path_with}")

    print("\n" + "=" * 60)
    print("✓ AUDIOS GENERADOS EXITOSAMENTE:")
    print(f"  1. [Sin Humanizar]: {os.path.abspath(path_without)}")
    print(f"  2. [Con Humanizar]: {os.path.abspath(path_with)}")
    print("=" * 60)

if __name__ == "__main__":
    create_demo_audios()
