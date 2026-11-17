"""
==============================================================================
Pruebas Unitarias e Integración: Historial de Conversaciones (ChatGPT Style)
==============================================================================
Valida que:
1. Las operaciones CRUD de sesiones en SQLite (creación, listado, renombrado, eliminación)
   funcionen con integridad referencial y marcas temporales.
2. La persistencia y recuperación de mensajes por conversación sea exacta y ordenada.
3. El generador de títulos inteligente (Auto-Titling) con LLaMA 3.2 y fallback heurístico
   asigne nombres concisos sin comillas ni prefijos.
4. Los endpoints REST (/api/sessions, /api/sessions/{id}/title, /api/sessions/{id}/generate-title, etc.)
   respondan con los códigos y payloads correctos.
5. El error de síntesis automática de notas ('urllib' is not defined) quede completamente resuelto.
6. La estructura visual, scripts modulares (history-drawer.js) y estilos CSS existan en el frontend.
==============================================================================
"""

import os
import time
import unittest
import sys
import asyncio

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database
import server
import urllib.request

class TestConversationHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

        # Mock de Ollama para pruebas unitarias instantáneas (<0.1s)
        cls.orig_urlopen = urllib.request.urlopen
        def mock_urlopen(req, timeout=None):
            class MockResponse:
                def __init__(self):
                    self.status = 200
                def read(self):
                    return b'{"message": {"content": "Pr\xc3\xa1ctica de Ingl\xc3\xa9s Tech"}}'
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return MockResponse()
        urllib.request.urlopen = mock_urlopen
        
        index_html_path = os.path.join(PROJECT_ROOT, "static", "index.html")
        style_css_path = os.path.join(PROJECT_ROOT, "static", "style.css")
        history_js_path = os.path.join(PROJECT_ROOT, "static", "js", "history-drawer.js")

        with open(index_html_path, "r", encoding="utf-8") as f:
            cls.html = f.read()
        with open(style_css_path, "r", encoding="utf-8") as f:
            cls.css = f.read()
        with open(history_js_path, "r", encoding="utf-8") as f:
            cls.history_js = f.read()

    @classmethod
    def tearDownClass(cls):
        urllib.request.urlopen = cls.orig_urlopen

    def test_01_session_crud_database(self):
        """Valida creación, obtención, actualización de título y eliminación en SQLite."""
        test_session_id = f"test-sess-{int(time.time() * 1000)}"
        
        # 1. Crear sesión
        created_id = database.create_or_get_session(test_session_id, mode="es", voice="ef_dora", title="Charla Inicial")
        self.assertEqual(created_id, test_session_id)

        # 2. Obtener sesión por ID
        sess = database.get_session_by_id(test_session_id)
        self.assertIsNotNone(sess)
        self.assertEqual(sess["title"], "Charla Inicial")
        self.assertEqual(sess["language_mode"], "es")

        # 3. Renombrar sesión
        renamed = database.update_session_title(test_session_id, "Conversación de Arquitectura de Software")
        self.assertTrue(renamed)
        sess_updated = database.get_session_by_id(test_session_id)
        self.assertEqual(sess_updated["title"], "Conversación de Arquitectura de Software")

        # 4. Listar sesiones
        all_sessions = database.get_all_sessions(limit=100)
        matching = [s for s in all_sessions if s["id"] == test_session_id]
        self.assertEqual(len(matching), 1)

        # 5. Eliminar sesión
        deleted = database.delete_session(test_session_id)
        self.assertTrue(deleted)
        self.assertIsNone(database.get_session_by_id(test_session_id))

    def test_02_session_messages_persistence(self):
        """Valida que los mensajes se persistan y recuperen en orden cronológico por sesión."""
        sess_id = f"test-msgs-{int(time.time() * 1000)}"
        database.create_or_get_session(sess_id, mode="en", title="Práctica de Entrevista")

        # Guardar 3 turnos
        database.save_message(sess_id, "user", "Tell me about your Python experience", turn_id="t1", stt_ms=140)
        database.save_message(sess_id, "assistant", "I have extensive experience with FastAPI and PyTorch.", turn_id="t1")
        database.save_message(sess_id, "user", "What about CUDA optimizations?", turn_id="t2", stt_ms=160)

        msgs = database.get_session_messages(sess_id)
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[0]["content"], "Tell me about your Python experience")
        self.assertEqual(msgs[1]["role"], "assistant")
        self.assertEqual(msgs[2]["role"], "user")

        # Limpieza
        database.delete_session(sess_id)

    def test_03_auto_titling_fallback_and_formatting(self):
        """Valida la generación de títulos automáticos con fallback heurístico limpio."""
        sess_id = f"test-autotitle-{int(time.time() * 1000)}"
        database.create_or_get_session(sess_id, mode="es", title="Nueva conversación")

        database.save_message(sess_id, "user", "Explícame cómo funcionan los transformadores y atención")
        database.save_message(sess_id, "assistant", "Los transformadores usan un mecanismo de auto-atención...")

        title = database.generate_ai_session_title(sess_id)
        self.assertIsInstance(title, str)
        self.assertGreater(len(title), 0)
        self.assertNotIn('"', title)
        self.assertNotIn("Título:", title)

        # Verificar que el título se guardó en la base de datos
        sess = database.get_session_by_id(sess_id)
        self.assertEqual(sess["title"], title)

        # Limpieza
        database.delete_session(sess_id)

    def test_04_api_session_endpoints(self):
        """Valida los endpoints REST /api/sessions para el cliente web."""
        # 1. Crear nueva sesión vía API
        create_res = server.api_create_session({"mode": "es", "title": "Sesión de Prueba REST"})
        self.assertEqual(create_res["status"], "ok")
        new_id = create_res["session_id"]

        # 2. Listar sesiones
        list_res = server.api_get_sessions()
        self.assertEqual(list_res["status"], "ok")
        sessions = list_res.get("sessions", [])
        self.assertTrue(any(s["id"] == new_id for s in sessions))

        # 3. Renombrar sesión vía API
        rename_res = server.api_update_session_title(new_id, {"title": "Título Modificado por API"})
        self.assertEqual(rename_res["status"], "ok")
        self.assertEqual(rename_res["title"], "Título Modificado por API")

        # 4. Obtener mensajes
        msgs_res = server.api_get_session_messages(new_id)
        self.assertEqual(msgs_res["status"], "ok")
        self.assertIn("messages", msgs_res)

        # 5. Generar título inteligente
        gen_title_res = server.api_generate_session_title(new_id)
        self.assertEqual(gen_title_res["status"], "ok")
        self.assertIn("title", gen_title_res)

        # 6. Eliminar sesión vía API
        del_res = server.api_delete_session(new_id)
        self.assertEqual(del_res["status"], "ok")
        self.assertTrue(del_res["deleted"])

    def test_05_notes_synthesis_no_urllib_name_error(self):
        """Valida que /api/notes/synthesize no falle con 'name urllib is not defined'."""
        nid = database.save_voice_note("Reunión con el equipo a las 3 PM", title="Reunión")
        data = server.api_synthesize_notes()
        self.assertEqual(data["status"], "ok")
        summary = data.get("summary", "")
        self.assertNotIn("name 'urllib' is not defined", summary)
        self.assertGreater(len(summary), 0)
        database.delete_voice_note(nid)

    def test_06_ui_elements_and_styles(self):
        """Valida la presencia del botón de chats, drawer lateral, script y clases CSS."""
        # HTML
        self.assertIn('id="btn-open-history-drawer"', self.html)
        self.assertIn('id="header-history-counter"', self.html)
        self.assertIn('id="history-drawer"', self.html)
        self.assertIn('id="history-drawer-overlay"', self.html)
        self.assertIn('id="btn-close-history-drawer"', self.html)
        self.assertIn('id="btn-new-chat-drawer"', self.html)
        self.assertIn('id="history-search-input"', self.html)
        self.assertIn('id="history-cards-container"', self.html)
        self.assertIn('/static/js/history-drawer.js', self.html)

        # CSS
        self.assertIn('.history-header-btn', self.css)
        self.assertIn('.history-drawer', self.css)
        self.assertIn('.btn-new-chat-action', self.css)
        self.assertIn('.history-item', self.css)
        self.assertIn('.history-action-btn', self.css)

        # JS
        self.assertIn('HistoryDrawerManager', self.history_js)
        self.assertIn('fetchSessions', self.history_js)
        self.assertIn('renameSession', self.history_js)
        self.assertIn('deleteSession', self.history_js)
        self.assertIn('generateAiTitle', self.history_js)

if __name__ == "__main__":
    unittest.main()
