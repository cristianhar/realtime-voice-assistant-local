import unittest
import sys
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.chunker import SentenceChunker
from core.llm import build_ollama_payload

class TestSynchronizationAndTiming(unittest.TestCase):
    """
    Tests de sincronización de flujo conversacional:
    - Validación de límites de tokens del LLM (anti-truncamiento mid-word).
    - Segmentación natural fluida y sin micro-cortes ("frena todavía").
    - Contrato de sincronización cliente-servidor (AudioPlayerManager y app.js).
    """

    def test_num_predict_sufficient_headroom(self):
        """
        Verifica que num_predict en build_ollama_payload tenga suficiente margen (>= 100 tokens),
        impidiendo que el LLM quede 'corto' o corte palabras por la mitad (ej: 'hab' en vez de 'hablamos').
        """
        payload = build_ollama_payload([{"role": "user", "content": "Hola"}])
        options = payload.get("options", {})
        num_predict = options.get("num_predict", 0)

        self.assertGreaterEqual(
            num_predict, 100,
            f"num_predict ({num_predict}) es demasiado bajo; causa truncamiento prematuro de respuestas."
        )

    def test_user_reported_case_sentence_coherence(self):
        """
        Prueba el caso exacto reportado por Cristian:
        'Es un tema muy interesante, especialmente con la Inteligencia Artificial que estamos trabajando en actualmente. ¿Qué te parece si hablamos de ello?'
        Verifica que:
        1. No corte prematuramente en 'Es un tema muy interesante,' (5 palabras).
        2. Genere oraciones completas con sentido y puntuación canónica.
        """
        tokens = (
            "Es un tema muy interesante, especialmente con la Inteligencia Artificial "
            "que estamos trabajando en actualmente. ¿Qué te parece si hablamos de ello?"
        ).split()

        buffer = ""
        is_first = True
        chunks = []

        for token in tokens:
            buffer += (" " if buffer else "") + token
            ready, remaining, should_split = SentenceChunker.extract_ready_sentence(buffer, is_first_chunk=is_first)
            if should_split:
                chunks.append(ready)
                buffer = remaining
                is_first = False

        if buffer.strip():
            chunks.append(buffer.strip())

        # Debe haber dividido en 3 bloques canónicamente puntuados (, . ?) sin cortar palabras en medio
        self.assertEqual(len(chunks), 3, f"Se esperaban 3 chunks puntuados, se obtuvieron: {chunks}")
        self.assertTrue(chunks[0].endswith(","))
        self.assertEqual(chunks[0], "Es un tema muy interesante,")
        self.assertTrue(chunks[1].endswith("actualmente."))
        self.assertTrue(chunks[2].endswith("de ello?"))

        # Cada chunk tiene longitud suficiente y no corta preposiciones
        for c in chunks:
            self.assertGreaterEqual(len(c.split()), 4, f"Chunk demasiado corto: {c}")

    def test_audio_player_sync_contract(self):
        """
        Verifica que static/js/audio-player.js implemente los métodos de sincronización
        por turnos (startTurn, markTurnComplete, finalizeTurn, graceTimeout)
        y prevenga la re-ejecución del sonido de respiración en mitad de turno.
        """
        player_path = os.path.join(PROJECT_ROOT, "static", "js", "audio-player.js")
        self.assertTrue(os.path.exists(player_path))

        with open(player_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("startTurn", code, "Falta método startTurn en AudioPlayerManager")
        self.assertIn("markTurnComplete", code, "Falta método markTurnComplete en AudioPlayerManager")
        self.assertIn("finalizeTurn", code, "Falta método finalizeTurn en AudioPlayerManager")
        self.assertIn("graceTimeout", code, "Falta graceTimeout para evitar parones entre chunks")
        self.assertIn("window.voiceHumanizer.playPreSpeechBreath", code)

    def test_app_js_turn_sync_integration(self):
        """
        Verifica que static/app.js comunique los inicios y finales de turno
        a audioPlayer para sincronizar el estado del orbe y evitar parones.
        """
        app_path = os.path.join(PROJECT_ROOT, "static", "app.js")
        with open(app_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("audioPlayer.startTurn", code, "app.js debe invocar audioPlayer.startTurn al enviar turnos")
        self.assertIn("audioPlayer.markTurnComplete", code, "app.js debe invocar audioPlayer.markTurnComplete en ai_done")

if __name__ == "__main__":
    unittest.main()
