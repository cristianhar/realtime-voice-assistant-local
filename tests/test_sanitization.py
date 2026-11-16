import unittest
from core.tts import clean_tts_text
from core.utils import is_text_spanish

class TestSanitizationAndUtils(unittest.TestCase):
    def test_strip_markdown_asterisks(self):
        text = "*sonríe cálidamente* Hola amigo, ¿cómo estás? *laughs*"
        clean = clean_tts_text(text)
        self.assertNotIn("*", clean)
        self.assertNotIn("sonríe", clean)
        self.assertNotIn("laughs", clean)
        self.assertIn("Hola amigo, ¿cómo estás?", clean)

    def test_strip_parentheses(self):
        text = "Hello (smiling gently) good morning to you!"
        clean = clean_tts_text(text)
        self.assertNotIn("smiling", clean)
        self.assertEqual(clean, "Hello good morning to you!")

    def test_preserve_spanish_accents_and_punctuation(self):
        text = "¡Excelente! ¿Vendrás mañana a las 3:00 p.m. con el señor Núñez?"
        clean = clean_tts_text(text)
        self.assertIn("¡Excelente!", clean)
        self.assertIn("¿Vendrás", clean)
        self.assertIn("Núñez", clean)

    def test_strip_emojis(self):
        text = "¡Hola mundo! 🎙️ 🚀 ✨ ¿Todo bien? 😊"
        clean = clean_tts_text(text)
        self.assertNotIn("🎙️", clean)
        self.assertNotIn("🚀", clean)
        self.assertNotIn("😊", clean)
        self.assertIn("¡Hola mundo!", clean)

    def test_spanish_detection(self):
        self.assertTrue(is_text_spanish("Hola, ¿cómo te encuentras hoy?"))
        self.assertTrue(is_text_spanish("Buenos días amigo"))
        self.assertTrue(is_text_spanish("Quiero hacer una consulta"))
        self.assertFalse(is_text_spanish("Hello my friend, how are you today?"))
        self.assertFalse(is_text_spanish("Let's practice some English pronunciation"))

if __name__ == "__main__":
    unittest.main()

