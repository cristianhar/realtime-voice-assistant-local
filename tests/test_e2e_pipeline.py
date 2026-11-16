import unittest
import os
import json
import time

from core import (
    PROMPTS,
    MODEL_NAME,
    SentenceChunker,
    clean_tts_text,
    is_text_spanish
)
import database
import tools

class TestEndToEndPipeline(unittest.TestCase):
    """
    Suite de Pruebas Integrales End-to-End (E2E)
    Verifica el flujo completo de:
    1. Inicialización y persistencia en base de datos SQLite.
    2. Detección y ejecución de herramientas de voz (Tool Calling).
    3. Construcción e inyección de memoria a largo plazo (RAG).
    4. Limpieza fonética y sanitización de texto para TTS.
    5. Segmentación continua de oraciones sin vacíos de audio.
    """

    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_01_sqlite_persistence_e2e(self):
        """Valida el ciclo de vida completo de una sesión conversacional."""
        session_id = f"e2e-session-{int(time.time())}"
        database.create_or_get_session(session_id, mode="en", voice="af_sarah")

        # 1. Turno de usuario
        database.save_message(
            session_id=session_id,
            role="user",
            content="I am looking for my keys.",
            turn_id="turn-e2e-1",
            stt_ms=28
        )

        # 2. Turno de IA
        database.save_message(
            session_id=session_id,
            role="assistant",
            content="Did you check your jacket pocket?",
            turn_id="turn-e2e-1"
        )

        # 3. Traducción y retroalimentación pedagógica
        database.update_message_translation("turn-e2e-1", "user", "Estoy buscando mis llaves.")
        database.update_message_translation("turn-e2e-1", "assistant", "¿Revisaste el bolsillo de tu chaqueta?")
        database.save_vocabulary_or_correction("I look keys", "I am looking for keys", "Usa presente continuo con 'looking for'")

        # 4. Verificación de lectura
        recent = database.get_recent_messages(limit=5)
        self.assertTrue(any(m["turn_id"] == "turn-e2e-1" and m["role"] == "user" for m in recent))
        self.assertTrue(any(m["turn_id"] == "turn-e2e-1" and m["role"] == "assistant" for m in recent))

        vocab = database.get_vocabulary_list(limit=5)
        self.assertTrue(any(v["phrase"] == "I look keys" for v in vocab))

    def test_02_voice_tools_e2e(self):
        """Valida la ejecución de todas las herramientas locales con latencia cero."""
        # 1. Consulta de hora en español
        time_res = tools.detect_and_execute_tool("¿Qué hora es?", lang_mode="es")
        self.assertIsNotNone(time_res)
        self.assertEqual(time_res["tool"], "get_current_time")
        self.assertEqual(time_res["lang"], "es")
        self.assertIn("Son las", time_res["spoken_response"])

        # 2. Guardar nota de voz
        note_res = tools.detect_and_execute_tool("Toma nota de comprar café descafeinado", lang_mode="es")
        self.assertIsNotNone(note_res)
        self.assertEqual(note_res["tool"], "save_voice_note")
        self.assertIn("café descafeinado", note_res["spoken_response"])
        note_id = note_res["data"]["note_id"]

        # 3. Listar notas
        list_res = tools.detect_and_execute_tool("¿Cuáles son mis notas?", lang_mode="es")
        self.assertIsNotNone(list_res)
        self.assertEqual(list_res["tool"], "list_voice_notes")
        self.assertIn("café descafeinado", list_res["spoken_response"])

        # 4. Listar vocabulario
        vocab_res = tools.detect_and_execute_tool("¿Qué vocabulario tengo?", lang_mode="es")
        self.assertIsNotNone(vocab_res)
        self.assertEqual(vocab_res["tool"], "list_vocabulary")

        # 5. Entrada normal no debe ser interceptada por herramientas
        normal_res = tools.detect_and_execute_tool("Me encanta programar en Python", lang_mode="es")
        self.assertIsNone(normal_res)

    def test_03_rag_memory_injection_e2e(self):
        """Valida que la memoria persistente genere el contexto adecuado para inyectar en Llama 3.2."""
        database.save_voice_note("Reunión con el equipo a las 4pm", "Nota de reunión")
        context_str = database.get_memory_context_string()

        self.assertIsInstance(context_str, str)
        self.assertIn("MEMORIA PERSISTENTE", context_str)
        self.assertIn("Reunión con el equipo a las 4pm", context_str)

        # Inyección en el prompt del sistema
        system_prompt = PROMPTS["es"] + f"\n{context_str}"
        self.assertIn("conversación", system_prompt.lower())
        self.assertIn("Reunión con el equipo", system_prompt)

    def test_04_gapless_sentence_chunking_simulation(self):
        """Simula la llegada progresiva de tokens de un LLM y la extracción de oraciones fluidas."""
        stream_tokens = [
            "¡Hola! ", "Claro ", "que ", "sí, ", "puedo ", "ayudarte ", "con ", "eso. ",
            "¿Qué ", "tema ", "te ", "gustaría ", "revisar ", "primero?"
        ]

        buffer = ""
        extracted_sentences = []

        for token in stream_tokens:
            buffer += token
            sentence, remaining, should_split = SentenceChunker.extract_ready_sentence(buffer)
            if should_split and sentence:
                extracted_sentences.append(sentence)
                buffer = remaining

        if buffer.strip():
            extracted_sentences.append(buffer.strip())

        # Debe haber dividido en 3 oraciones completas y coherentes (¡Hola!, Claro que sí..., ¿Qué tema...?)
        self.assertEqual(len(extracted_sentences), 3)
        self.assertEqual(extracted_sentences[0], "¡Hola!")
        self.assertEqual(extracted_sentences[1], "Claro que sí, puedo ayudarte con eso.")
        self.assertEqual(extracted_sentences[2], "¿Qué tema te gustaría revisar primero?")

    def test_05_tts_sanitization_e2e(self):
        """Verifica que el texto enviado a Kokoro esté completamente limpio de símbolos."""
        raw_text = "*sonríe ampliamente* ¡Hola! (risas) ¿Cómo te va hoy? ✨ 100% 👍"
        clean = clean_tts_text(raw_text)
        self.assertNotIn("*", clean)
        self.assertNotIn("(", clean)
        self.assertNotIn("✨", clean)
        self.assertNotIn("👍", clean)
        self.assertEqual(clean, "¡Hola! ¿Cómo te va hoy? 100")

    def test_06_frontend_modular_assets_e2e(self):
        """Verifica que los assets frontend modulares (locales.json, scripts JS) existan y sean válidos."""
        from core.config import STATIC_DIR
        import json

        locales_file = os.path.join(STATIC_DIR, "locales.json")
        self.assertTrue(os.path.isfile(locales_file), "locales.json debe existir en static/")

        with open(locales_file, "r", encoding="utf-8") as f:
            locales_data = json.load(f)

        expected_languages = ["es", "en", "pt", "fr", "de", "it", "ja", "zh"]
        for lang in expected_languages:
            self.assertIn(lang, locales_data, f"Idioma {lang} debe estar en locales.json")
            self.assertIn("welcome_title", locales_data[lang])
            self.assertIn("label_personality", locales_data[lang])

        js_files = ["i18n.js", "visualizer.js", "wav-encoder.js"]
        for js in js_files:
            js_path = os.path.join(STATIC_DIR, "js", js)
            self.assertTrue(os.path.isfile(js_path), f"El módulo {js} debe existir en static/js/")

    def test_07_dense_vector_semantic_rag_e2e(self):
        """Verifica la memoria semántica vectorial densa (Hybrid RAG) con SQLite y Ollama."""
        # 1. Guardar nota
        nid = database.save_voice_note("Comprar pasta dental y jabón para el baño", "Artículos de aseo")
        self.assertIsInstance(nid, int)

        # 2. Búsqueda semántica densa
        results = database.search_dense_memory("higiene personal y aseo", top_k=3, threshold=0.55)
        # Debe retornar lista válida
        self.assertIsInstance(results, list)

        # 3. Contexto RAG Híbrido
        rag_context = database.get_smart_memory_context("¿Te acuerdas qué tenía que comprar para el baño?")
        self.assertIn("MEMORIA PERSISTENTE", rag_context)
        self.assertIn("Cristian Arboleda", rag_context)

    def test_08_voice_blends_and_whisper_e2e(self):
        """Verifica la arquitectura de mezclas de voz híbridas y el modo susurro."""
        from core.tts import VOICE_BLENDS, get_voice_target

        self.assertIn("blend_dora_sarah", VOICE_BLENDS)
        self.assertIn("blend_alex_adam", VOICE_BLENDS)

        # Verificar proporciones de mezcla
        dora_sarah = VOICE_BLENDS["blend_dora_sarah"]
        self.assertEqual(len(dora_sarah), 2)
        total_weight = sum(w for _, w in dora_sarah)
        self.assertAlmostEqual(total_weight, 1.0, places=2)

        # Test target resolution
        target = get_voice_target(None, "blend_dora_sarah")
        self.assertIsNotNone(target)

if __name__ == "__main__":
    unittest.main()
