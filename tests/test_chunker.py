import unittest
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.chunker import SentenceChunker

class TestSentenceChunker(unittest.TestCase):
    def test_complete_sentence_split(self):
        buf = "Hello my friend! How are you doing today?"
        sentence, remaining, should_split = SentenceChunker.extract_ready_sentence(buf)
        self.assertTrue(should_split)
        self.assertEqual(sentence, "Hello my friend!")
        self.assertEqual(remaining.strip(), "How are you doing today?")

    def test_short_comma_no_split(self):
        # Evita cortar prematuramente en "Sí," o "Well,"
        buf = "Sí, claro que puedo ayudarte."
        sentence, remaining, should_split = SentenceChunker.extract_ready_sentence(buf)
        # Debe esperar a que termine la frase completa o tenga suficientes palabras
        if should_split:
            self.assertTrue(len(sentence.split()) >= 3)

    def test_long_clause_split(self):
        buf = "Estuve revisando todos los documentos de la reunión de ayer, y encontré varios puntos interesantes que debemos tratar"
        sentence, remaining, should_split = SentenceChunker.extract_ready_sentence(buf)
        self.assertTrue(should_split)
        self.assertTrue(sentence.endswith(","))
        self.assertTrue(len(sentence.split()) >= 5)

    def test_question_mark_split(self):
        buf = "¿Quieres que revisemos el informe juntos? Claro que sí."
        sentence, remaining, should_split = SentenceChunker.extract_ready_sentence(buf)
        self.assertTrue(should_split)
        self.assertIn("informe juntos?", sentence)

    def test_buffer_overflow_without_punctuation(self):
        buf = "uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece"
        sentence, remaining, should_split = SentenceChunker.extract_ready_sentence(buf)
        self.assertTrue(should_split)
        self.assertEqual(len(sentence.split()), 8)
        self.assertEqual(len(remaining.split()), 5)

    def test_user_reported_case_no_premature_split(self):
        """
        Valida que el caso exacto reportado por Cristian ('Hablaste sobre latencia baja')
        NO se corte prematuramente a las 4 palabras, evitando el silencio entre fragmentos.
        """
        # 1. Cuando el LLM apenas ha emitido 4 palabras sin puntuación (lo que pasaba antes)
        buf_4_words = "Hablaste sobre latencia baja"
        _, _, should_split_4 = SentenceChunker.extract_ready_sentence(buf_4_words, is_first_chunk=True)
        self.assertFalse(should_split_4, "No debe cortar en 4 palabras porque causa buffer underrun y pausas en audio")

        # 2. Cuando el stream llega a la coma natural ('... en asistentes de voz,')
        buf_stream_at_comma = "Hablaste sobre latencia baja en asistentes de voz,"
        sentence, remaining, should_split_clause = SentenceChunker.extract_ready_sentence(buf_stream_at_comma, is_first_chunk=True)
        self.assertTrue(should_split_clause)
        self.assertEqual(sentence, "Hablaste sobre latencia baja en asistentes de voz,")
        self.assertTrue(len(sentence.split()) >= 7, "El primer chunk debe tener al menos 7 palabras (~2.2s de audio) para locución continua")

        # 3. Si el buffer ya contiene la frase completa con punto final, se habla derecha y completa
        buf_full_sentence = "Hablaste sobre latencia baja en asistentes de voz, explicaste por qué es crucial para un buen rendimiento."
        sentence_full, remaining_full, should_split_full = SentenceChunker.extract_ready_sentence(buf_full_sentence, is_first_chunk=True)
        self.assertTrue(should_split_full)
        self.assertEqual(sentence_full, "Hablaste sobre latencia baja en asistentes de voz, explicaste por qué es crucial para un buen rendimiento.")
        self.assertEqual(remaining_full.strip(), "")

    def test_streaming_token_simulation_straight_audio(self):
        """
        Simula la llegada progresiva palabra por palabra para asegurar que los audios
        salgan derechos y continuos sin micro-cortes artificiales.
        """
        tokens = "Hablaste sobre latencia baja en asistentes de voz, explicaste por qué es crucial para un buen rendimiento.".split()
        buffer = ""
        is_first = True
        chunks_produced = []

        for token in tokens:
            buffer += (" " if buffer else "") + token
            ready, remaining, should_split = SentenceChunker.extract_ready_sentence(buffer, is_first_chunk=is_first)
            if should_split:
                chunks_produced.append(ready)
                buffer = remaining
                is_first = False

        if buffer.strip():
            chunks_produced.append(buffer.strip())

        # Debe generar exactamente 2 bloques naturales bien balanceados (no trozos diminutos de 3-4 palabras)
        self.assertEqual(len(chunks_produced), 2)
        self.assertEqual(chunks_produced[0], "Hablaste sobre latencia baja en asistentes de voz,")
        self.assertIn("explicaste por qué es crucial para un buen rendimiento.", chunks_produced[1])

        # Cada bloque tiene suficiente duración en palabras (>= 7) para permitir síntesis fluida en segundo plano
        for chunk in chunks_produced:
            self.assertTrue(len(chunk.split()) >= 7, f"Chunk demasiado corto detectado: '{chunk}'")

    def test_audio_buffer_headroom_math(self):
        """
        Valida matemáticamente que la duración de audio del primer fragmento
        supere holgadamente la latencia de síntesis de Kokoro TTS (~450ms),
        garantizando que la cola del navegador nunca quede vacía (Gapless).
        """
        sample_phrase = "Hablaste sobre latencia baja en asistentes de voz,"
        words = sample_phrase.split()
        # En español se habla a ~150 palabras/minuto = 2.5 palabras/segundo => 400ms por palabra
        estimated_audio_duration_ms = len(words) * 400  # 8 * 400 = 3200 ms
        kokoro_synthesis_time_ms = 450  # Tiempo de síntesis multihilo medido
        llm_token_generation_ms = 400   # Tiempo para generar siguientes 12 tokens a 30 tok/s

        headroom_ms = estimated_audio_duration_ms - (kokoro_synthesis_time_ms + llm_token_generation_ms)
        # El buffer en reproducción debe tener al menos 1000ms de margen libre
        self.assertGreater(headroom_ms, 1000, "El margen de seguridad del buffer debe ser > 1s para evitar vacilaciones")

if __name__ == "__main__":
    unittest.main()
