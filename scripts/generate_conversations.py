"""
generate_conversations.py - Generates realistic multi-turn full-duplex conversations
with natural humanizer cadences in both Spanish and English.
"""
import os
import sys
import numpy as np
import soundfile as sf

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.tts import load_tts_model, clean_tts_text

def build_conversation(tts_model, turns, output_path, lang):
    sr = 24000
    audio_segments = []
    pause_between_turns = np.zeros(int(sr * 0.45), dtype=np.float32)

    print(f"\n--- Generando conversación ({lang.upper()}): {output_path} ---")

    for i, (speaker, voice, text, speed) in enumerate(turns):
        print(f"  [{speaker} ({voice})]: \"{text}\"")
        cleaned = clean_tts_text(text)
        samples, _ = tts_model.create(
            cleaned,
            voice=voice,
            speed=speed,
            lang=lang,
            sentence_pause=0.22,
            clause_pause=0.12
        )
        audio_segments.append(samples)
        if i < len(turns) - 1:
            audio_segments.append(pause_between_turns)

    full_audio = np.concatenate(audio_segments)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sf.write(output_path, full_audio, sr)
    dur = len(full_audio) / sr
    print(f"-> [OK] Guardado: {output_path} ({dur:.2f} segundos)\n")
    return output_path

def main():
    print("[1/3] Inicializando Kokoro TTS Engine...")
    tts_model = load_tts_model()

    # Conversación 1: Español (Tema: Exploración de Marte & IA)
    # Usuario: em_alex, Asistente IA Humanizada: ef_dora
    dialogue_es = [
        (
            "Usuario",
            "em_alex",
            "Oye, ¿tú crees que los humanos realmente llegaremos a vivir en Marte en los próximos veinte años?",
            1.05
        ),
        (
            "Asistente IA",
            "ef_dora",
            "A ver... técnicamente es posible, pero el mayor reto no es el cohete, sino sobrevivir a la radiación cósmica y producir alimento sustentable allá.",
            1.05
        ),
        (
            "Usuario",
            "em_alex",
            "¿Y qué papel juega la inteligencia artificial en una misión de ese calibre?",
            1.05
        ),
        (
            "Asistente IA",
            "ef_dora",
            "Bueno... sin inteligencia artificial sería inviable. Se necesita control autónomo en tiempo real porque las comunicaciones con la Tierra tienen hasta veinte minutos de retraso.",
            1.05
        )
    ]

    # Conversación 2: Inglés (Tema: AI & Human Creativity)
    # User: am_adam, AI Assistant Humanized: af_sarah
    dialogue_en = [
        (
            "User",
            "am_adam",
            "Hey, do you think artificial intelligence will ever replace human creativity in music and writing?",
            1.08
        ),
        (
            "AI Assistant",
            "af_sarah",
            "Well... I don't see it as replacement, but rather as an amplification tool. AI can generate complex chord progressions, but genuine emotional depth still comes from human experience.",
            1.08
        ),
        (
            "User",
            "am_adam",
            "That's a relief! So artists should embrace it instead of fearing it?",
            1.08
        ),
        (
            "AI Assistant",
            "af_sarah",
            "Exactly! The most forward-thinking creators are already using AI as their tireless co-pilot.",
            1.08
        )
    ]

    path_es = os.path.join("static", "audio", "conversation_demo_es.wav")
    path_en = os.path.join("static", "audio", "conversation_demo_en.wav")

    build_conversation(tts_model, dialogue_es, path_es, lang="es")
    build_conversation(tts_model, dialogue_en, path_en, lang="en-us")

    print("=" * 70)
    print("✓ CONVERSACIONES HUMANIZADAS GENERADAS:")
    print(f"  1. Español: {os.path.abspath(path_es)}")
    print(f"  2. Inglés:  {os.path.abspath(path_en)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
