import unittest
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

if __name__ == "__main__":
    unittest.main()
