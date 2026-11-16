import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database
import tools

class TestToolsAndMemory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        database.save_voice_note("Comprar leche y pan", "Nota de prueba")
        database.save_vocabulary_or_correction("I have 20 years", "I am 20 years old", "En inglés la edad se dice con to be")

    def test_time_tool_es(self):
        res = tools.detect_and_execute_tool("¿Qué hora es?", lang_mode="es")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "get_current_time")
        self.assertTrue(any(w in res["spoken_response"] for w in ["Son las", "Es la una", "la una", "Son"]))
        self.assertEqual(res["lang"], "es")

    def test_time_tool_en(self):
        res = tools.detect_and_execute_tool("Hey, what time is it?", lang_mode="en")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "get_current_time")
        self.assertIn("It is", res["spoken_response"])
        self.assertEqual(res["lang"], "en")

    def test_save_voice_note_es(self):
        res = tools.detect_and_execute_tool("Toma nota de comprar café y pan", lang_mode="es")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "save_voice_note")
        self.assertIn("comprar café y pan", res["spoken_response"])
        self.assertIn("note_id", res["data"])

    def test_save_voice_note_en(self):
        res = tools.detect_and_execute_tool("Take a note buy new headphones", lang_mode="en")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "save_voice_note")
        self.assertIn("buy new headphones", res["spoken_response"])

    def test_list_notes(self):
        res = tools.detect_and_execute_tool("¿Qué notas tengo?", lang_mode="es")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "list_voice_notes")
        self.assertIn("notas", res["spoken_response"])

    def test_memory_context_string(self):
        context = database.get_memory_context_string()
        self.assertIsInstance(context, str)
        self.assertIn("MEMORIA PERSISTENTE", context)
        self.assertIn("NOTAS", context)

    def test_list_vocabulary_es(self):
        res = tools.detect_and_execute_tool("¿Qué vocabulario tengo?", lang_mode="es")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "list_vocabulary")
        self.assertIn("frases", res["spoken_response"])

    def test_list_vocabulary_en(self):
        res = tools.detect_and_execute_tool("What vocabulary did I learn?", lang_mode="en")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "list_vocabulary")
        self.assertIn("phrases", res["spoken_response"].lower())
        self.assertIn("vocabulary", res["display_response"].lower())

    def test_database_persistence_cycle(self):
        sess_id = f"test-sess-{database.time.time()}"
        database.create_or_get_session(sess_id, mode="en", voice="af_sarah")
        
        # Guardar turnos
        database.save_message(sess_id, "user", "Hello there", turn_id="t1", stt_ms=45)
        database.save_message(sess_id, "assistant", "Hello! How are you?", turn_id="t1", ttfa_ms=210)
        database.update_message_translation("t1", "user", "Hola a todos")
        
        # Recuperar mensajes
        messages = database.get_recent_messages(limit=5)
        self.assertTrue(len(messages) >= 2)
        
        # Recuperar notas
        note_id = database.save_voice_note("Revisar código fuente", "Nota de código")
        self.assertIsInstance(note_id, int)
        notes = database.get_recent_notes(limit=5)
        self.assertTrue(any(n["content"] == "Revisar código fuente" for n in notes))

    def test_user_profile(self):
        profile = database.get_user_profile()
        self.assertIn("name", profile)
        self.assertEqual(profile["name"], "Cristian Arboleda")
        database.set_user_profile_value("city", "Medellín")
        updated = database.get_user_profile()
        self.assertEqual(updated.get("city"), "Medellín")

    def test_fts5_semantic_search(self):
        database.save_voice_note("Comprar aguacates y plátanos maduros en el mercado", "Compras de fruta")
        results = database.search_fts_memory("aguacates plátanos")
        self.assertTrue(len(results["notes"]) > 0)
        self.assertTrue(any("aguacates" in n["content"].lower() for n in results["notes"]))

    def test_smart_memory_context(self):
        context = database.get_smart_memory_context(query="¿Te acuerdas de los aguacates?")
        self.assertIn("Cristian Arboleda", context)
        self.assertIn("aguacates", context.lower())

    def test_no_tool_fallback_to_llm(self):
        res = tools.detect_and_execute_tool("Hola, ¿cómo estás hoy amigo?", lang_mode="es")
        self.assertIsNone(res)

    def test_hardware_status_tool_es(self):
        res = tools.detect_and_execute_tool("¿Cómo está la GPU y el rendimiento?", lang_mode="es")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "get_hardware_status")
        self.assertEqual(res["lang"], "es")
        self.assertTrue("GPU" in res["display_response"] or "Sistema" in res["display_response"])

    def test_hardware_status_tool_en(self):
        res = tools.detect_and_execute_tool("How is the GPU temperature and vram usage?", lang_mode="en")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "get_hardware_status")
        self.assertEqual(res["lang"], "en")
        self.assertTrue("GPU" in res["display_response"] or "System" in res["display_response"])

    def test_launch_application_tool(self):
        # Usar unittest.mock para evitar abrir ventanas físicas en el runner de pruebas
        from unittest.mock import patch
        with patch("subprocess.Popen") as mock_popen:
            res = tools.detect_and_execute_tool("Abre la calculadora por favor", lang_mode="es")
            self.assertIsNotNone(res)
            self.assertEqual(res["tool"], "launch_application")
            self.assertEqual(res["lang"], "es")
            self.assertIn("calculadora", res["spoken_response"].lower())
            mock_popen.assert_called_once()

    def test_personalities_prompt_generation(self):
        from core.config import get_system_prompt, PERSONALITIES
        self.assertIn("interviewer", PERSONALITIES)
        for p_key in PERSONALITIES.keys():
            prompt_es = get_system_prompt("es", personality=p_key)
            prompt_en = get_system_prompt("en", personality=p_key)
            self.assertIsInstance(prompt_es, str)
            self.assertIsInstance(prompt_en, str)
            self.assertTrue(len(prompt_es) > 50)
            self.assertTrue(len(prompt_en) > 50)

    def test_speed_control_tool_es(self):
        # 1. Más rápido
        res = tools.detect_and_execute_tool("habla un poco más rápido por favor", lang_mode="es")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "set_speech_speed")
        self.assertEqual(res["lang"], "es")
        self.assertEqual(res["data"]["speed"], 1.25)
        self.assertIn("uno punto veinticinco", res["spoken_response"])
        self.assertIn("1.25x", res["display_response"])

        # 2. Más despacio
        res_slow = tools.detect_and_execute_tool("habla más despacio", lang_mode="es")
        self.assertIsNotNone(res_slow)
        self.assertEqual(res_slow["data"]["speed"], 0.85)

        # 3. Velocidad normal
        res_norm = tools.detect_and_execute_tool("habla a ritmo normal", lang_mode="es")
        self.assertIsNotNone(res_norm)
        self.assertEqual(res_norm["data"]["speed"], 1.0)

    def test_speed_control_tool_en(self):
        res = tools.detect_and_execute_tool("please speak faster", lang_mode="en")
        self.assertIsNotNone(res)
        self.assertEqual(res["tool"], "set_speech_speed")
        self.assertEqual(res["lang"], "en")
        self.assertEqual(res["data"]["speed"], 1.25)

        res_slow = tools.detect_and_execute_tool("talk slower please", lang_mode="en")
        self.assertIsNotNone(res_slow)
        self.assertEqual(res_slow["data"]["speed"], 0.85)

    def test_search_web_tool(self):
        from unittest.mock import patch
        with patch("tools.search_web_smart") as mock_search:
            mock_search.return_value = {
                "type": "weather",
                "lead": "Medellin: +24°C",
                "details": ["Medellin: +24°C"]
            }
            res = tools.detect_and_execute_tool("busca en internet el clima en medellin", lang_mode="es")
            self.assertIsNotNone(res)
            self.assertEqual(res["tool"], "search_web")
            self.assertEqual(res["lang"], "es")
            self.assertIn("clima", res["spoken_response"].lower())
            self.assertIn("Medellin", res["display_response"])

if __name__ == "__main__":
    unittest.main()
