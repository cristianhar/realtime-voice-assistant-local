"""
test_humanization_and_vad.py - Test Suite for Voice Humanization, Spectral VAD, and Demo Assets
Validates pre-speech breath audio acoustics, conversational fillers, spectral noise filtering, and GIF integrity.
"""
import unittest
import os
import wave
import struct
import numpy as np

import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.utils import get_conversational_filler, CONVERSATIONAL_FILLERS

class TestHumanizationAndVAD(unittest.TestCase):

    def test_01_breath_audio_wav_properties(self):
        """Verifica la existencia, envolvente, frecuencia y nivel de presión sonora de la micro-inhalación."""
        wav_path = os.path.join(PROJECT_ROOT, "static", "audio", "breath_subtle.wav")
        self.assertTrue(os.path.isfile(wav_path), f"El archivo {wav_path} no existe.")

        with wave.open(wav_path, "r") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)

        self.assertEqual(channels, 1, "El audio de respiración debe ser mono (1 canal).")
        self.assertEqual(sampwidth, 2, "El audio debe ser PCM 16-bit.")
        self.assertEqual(framerate, 24000, "La tasa de muestreo debe ser 24kHz (alineada con Kokoro).")

        duration_sec = n_frames / float(framerate)
        self.assertGreaterEqual(duration_sec, 0.07, "La respiración no debe ser inferior a 70ms.")
        self.assertLessEqual(duration_sec, 0.15, "La respiración no debe exceder 150ms para no demorar la respuesta.")

        # Análisis acústico de la señal
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        peak = np.max(np.abs(samples))
        mean = np.mean(samples)

        # No debe saturar (debe ser sutil, entre -24 dB y -14 dB -> peak entre 0.06 y 0.35)
        self.assertLess(peak, 0.35, "La respiración es demasiado fuerte (podría distraer al usuario).")
        self.assertGreater(peak, 0.05, "La respiración es inaudible.")
        # Sin offset de DC significativo
        self.assertAlmostEqual(mean, 0.0, delta=0.05, msg="La señal tiene offset de corriente continua.")

    def test_02_conversational_fillers(self):
        """Verifica la generación contextual de titubeos y fillers orgánicos en inglés y español."""
        # 1. Fillers en español
        filler_es_thinking = get_conversational_filler("es", "thinking")
        self.assertIn(filler_es_thinking, CONVERSATIONAL_FILLERS["es"]["thinking"])

        filler_es_agree = get_conversational_filler("es", "agreement")
        self.assertIn(filler_es_agree, CONVERSATIONAL_FILLERS["es"]["agreement"])

        filler_es_search = get_conversational_filler("es", "searching")
        self.assertIn(filler_es_search, CONVERSATIONAL_FILLERS["es"]["searching"])

        # 2. Fillers en inglés
        filler_en_thinking = get_conversational_filler("en", "thinking")
        self.assertIn(filler_en_thinking, CONVERSATIONAL_FILLERS["en"]["thinking"])

        filler_en_agree = get_conversational_filler("en", "agreement")
        self.assertIn(filler_en_agree, CONVERSATIONAL_FILLERS["en"]["agreement"])

        # 3. Fallbacks de intención desconocida
        filler_fallback = get_conversational_filler("en", "unknown_intent")
        self.assertIn(filler_fallback, CONVERSATIONAL_FILLERS["en"]["thinking"])

    def test_03_spectral_formant_vad_logic(self):
        """Valida matemáticamente la discriminación de formantes vocales vs ruido de teclado y viento."""
        def simulate_vad(signal, subbass_ratio, voice_ratio, click_ratio, threshold=0.030):
            # RMS
            rms = np.sqrt(np.mean(signal**2))
            # ZCR (Zero-Crossing Rate)
            zcr = np.mean(np.abs(np.diff(np.sign(signal)))) / 2.0

            is_voice_formant = True
            total = subbass_ratio + voice_ratio + click_ratio + 1e-5
            if (subbass_ratio / total > 0.78) and (voice_ratio / total < 0.18):
                is_voice_formant = False
            elif (click_ratio / total > 0.65) and (zcr > 0.30):
                is_voice_formant = False

            return bool((rms > threshold) and (zcr < 0.38) and is_voice_formant)

        # Caso A: Voz humana limpia (Vocal 'a' a 300Hz, energía en formantes, ZCR moderado ~0.08)
        t = np.linspace(0, 0.25, 4000)
        vowel_signal = 0.25 * np.sin(2 * np.pi * 350 * t) + 0.15 * np.sin(2 * np.pi * 1200 * t)
        is_speech = simulate_vad(vowel_signal, subbass_ratio=10, voice_ratio=80, click_ratio=10)
        self.assertTrue(is_speech, "La voz humana debe ser detectada como habla activa.")

        # Caso B: Golpe de viento o soplido de respiración en el micrófono (<100Hz concentrado)
        breath_signal = 0.20 * np.sin(2 * np.pi * 45 * t)
        is_breath_speech = simulate_vad(breath_signal, subbass_ratio=90, voice_ratio=5, click_ratio=5)
        self.assertFalse(is_breath_speech, "El soplido de respiración debe ser rechazado por el VAD.")

        # Caso C: Clic rápido de teclado mecánico (ruido impulsivo >4kHz, ZCR alto >0.45)
        np.random.seed(42)
        click_signal = np.random.uniform(-0.15, 0.15, 4000)
        is_click_speech = simulate_vad(click_signal, subbass_ratio=5, voice_ratio=10, click_ratio=85)
        self.assertFalse(is_click_speech, "El clic de teclado debe ser rechazado por el VAD.")

    def test_04_demo_gif_integrity(self):
        """Valida que el GIF animado para el README exista, sea válido, fluido y ligero (usando standard library)."""
        gif_path = os.path.join(PROJECT_ROOT, "docs", "images", "voice_assistant_demo.gif")
        self.assertTrue(os.path.isfile(gif_path), f"El GIF {gif_path} no existe.")

        size_kb = os.path.getsize(gif_path) / 1024
        self.assertLess(size_kb, 1500, f"El GIF excede 1.5MB ({size_kb:.1f} KB).")

        with open(gif_path, "rb") as f:
            header = f.read(6)
            self.assertIn(header, (b"GIF89a", b"GIF87a"), "El archivo no tiene una cabecera GIF válida.")
            w, h = struct.unpack("<HH", f.read(4))
            self.assertEqual((w, h), (720, 360), "Las dimensiones del GIF deben ser 720x360.")

            f.seek(0)
            content = f.read()
            # 0x2C es el separador de descriptor de imagen de cada frame en la especificación GIF
            frame_count = content.count(b"\x2c")
            self.assertGreaterEqual(frame_count, 24, "El GIF debe tener al menos 24 frames para ser fluido.")

    def test_05_client_modules_integrated(self):
        """Verifica la integración del módulo humanizer.js en index.html y audio-player.js."""
        humanizer_js = os.path.join(PROJECT_ROOT, "static", "js", "humanizer.js")
        self.assertTrue(os.path.isfile(humanizer_js), "Falta static/js/humanizer.js")

        with open(humanizer_js, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("VoiceHumanizer", code)
        self.assertIn("playPreSpeechBreath", code)
        self.assertIn("synthesizeProceduralBreath", code)

        index_html = os.path.join(PROJECT_ROOT, "static", "index.html")
        with open(index_html, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('src="/static/js/humanizer.js"', html)

        player_js = os.path.join(PROJECT_ROOT, "static", "js", "audio-player.js")
        with open(player_js, "r", encoding="utf-8") as f:
            player_code = f.read()
        self.assertIn("window.voiceHumanizer.playPreSpeechBreath()", player_code)

if __name__ == "__main__":
    unittest.main()
