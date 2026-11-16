"""
test_agensi_skills_e2e.py - End-to-End Validation Suite for Agensi.io Skills Packages
Validates packaging spec conformance, root SKILL.md frontmatter, and executes all bundled scripts.
"""
import unittest
import os
import sys
import zipfile
import re
import asyncio
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGY_SKILLS_DIR = os.path.join(PROJECT_ROOT, "agensi_skills")

class TestAgensiSkillsE2E(unittest.TestCase):
    
    EXPECTED_SKILLS = [
        "realtime-voice-barge-in",
        "local-voice-tool-calling-memory",
        "kokoro-whisper-local-pipeline"
    ]

    def test_01_zip_packaging_and_spec_conformance(self):
        """Verifica que los 3 zips existan, pesen <50MB y contengan SKILL.md en la raíz con frontmatter válido."""
        for skill_name in self.EXPECTED_SKILLS:
            zip_path = os.path.join(AGY_SKILLS_DIR, f"{skill_name}.zip")
            self.assertTrue(os.path.isfile(zip_path), f"El archivo zip {zip_path} no existe.")
            
            # Verificar límite de 50 MB de Agensi
            size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            self.assertLess(size_mb, 50.0, f"El zip {skill_name} excede el límite de 50 MB ({size_mb:.2f} MB).")

            # Verificar estructura interna del zip
            with zipfile.ZipFile(zip_path, 'r') as zf:
                namelist = zf.namelist()
                self.assertIn("SKILL.md", namelist, f"SKILL.md no está en la raíz de {skill_name}.zip")

                # Verificar frontmatter de SKILL.md
                skill_content = zf.read("SKILL.md").decode("utf-8")
                self.assertTrue(skill_content.startswith("---"), f"SKILL.md en {skill_name} no inicia con frontmatter YAML (---).")
                self.assertIn(f"name: {skill_name}", skill_content, f"Nombre del skill no coincide en {skill_name}.")
                self.assertIn("description:", skill_content, f"Falta descripción en frontmatter de {skill_name}.")

                # Verificar presencia de carpetas mínimas requeridas por Agensi
                has_scripts = any(n.startswith("scripts/") for n in namelist)
                has_references = any(n.startswith("references/") for n in namelist)
                has_templates = any(n.startswith("templates/") for n in namelist)
                self.assertTrue(has_scripts, f"Falta carpeta scripts/ en {skill_name}.zip")
                self.assertTrue(has_references, f"Falta carpeta references/ en {skill_name}.zip")
                self.assertTrue(has_templates, f"Falta carpeta templates/ en {skill_name}.zip")

    def test_02_skill_1_barge_in_execution_e2e(self):
        """Ejecuta el arnés de prueba de interrupción <50ms de realtime-voice-barge-in."""
        skill_dir = os.path.join(AGY_SKILLS_DIR, "realtime-voice-barge-in")
        scripts_dir = os.path.join(skill_dir, "scripts")
        
        sys.path.insert(0, scripts_dir)
        try:
            import barge_in_harness
            latency = barge_in_harness.simulate_barge_in_cycle()
            self.assertLess(latency, 50.0)
        finally:
            if scripts_dir in sys.path:
                sys.path.remove(scripts_dir)

        # Validar template HTML del cliente de voz
        tpl_path = os.path.join(skill_dir, "templates", "voice_client_snippet.html")
        with open(tpl_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("RealtimeAudioProcessor", html)
        self.assertIn("interruptPlayback", html)
        self.assertIn("ws.send(JSON.stringify({ type: \"interrupt\" }))", html)

    def test_03_skill_2_tools_and_sqlite_memory_e2e(self):
        """Valida despacho heurístico <5ms y persistencia semántica FTS5 de local-voice-tool-calling-memory."""
        skill_dir = os.path.join(AGY_SKILLS_DIR, "local-voice-tool-calling-memory")
        scripts_dir = os.path.join(skill_dir, "scripts")
        
        sys.path.insert(0, scripts_dir)
        try:
            from tool_dispatcher import dispatch_local_tool
            from hybrid_sqlite_memory import SQLiteMemoryManager

            # 1. Probar despacho de herramientas
            handled, res = dispatch_local_tool("what time is it?")
            self.assertTrue(handled)
            self.assertIn("It is currently", res)

            handled_es, res_es = dispatch_local_tool("¿qué hora es?")
            self.assertTrue(handled_es)
            self.assertIn("Son las", res_es)

            handled_hw, res_hw = dispatch_local_tool("check hardware status")
            self.assertTrue(handled_hw)
            self.assertIn("System hardware summary:", res_hw)

            handled_noop, _ = dispatch_local_tool("tell me a fiction story")
            self.assertFalse(handled_noop)

            # 2. Probar memoria persistente FTS5
            mem = SQLiteMemoryManager(":memory:")
            mem.save_note("Reunión Agensi", "Llamada con Joeri el martes a las 3 PM para revisar skills")
            mem.save_note("Supermercado", "Comprar leche de almendras y café")

            results = mem.search_notes("reunión agensi")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Reunión Agensi")

            context = mem.get_context_for_prompt("cuándo es la reunión con Joeri?")
            self.assertIn("Reunión Agensi", context)
            self.assertIn("Llamada con Joeri", context)
        finally:
            if scripts_dir in sys.path:
                sys.path.remove(scripts_dir)

    def test_04_skill_3_kokoro_whisper_pipeline_e2e(self):
        """Valida sanitización TTS y mezcla de voces vectoriales de kokoro-whisper-local-pipeline."""
        skill_dir = os.path.join(AGY_SKILLS_DIR, "kokoro-whisper-local-pipeline")
        scripts_dir = os.path.join(skill_dir, "scripts")
        
        sys.path.insert(0, scripts_dir)
        try:
            from tts_kokoro_sanitizer import clean_for_tts, blend_voices

            # 1. Probar sanitización de texto para voz
            raw_text = "¡Hola Cristian! **Confirmado**, revisa https://agensi.io/sell `git push` *listo*! 🚀"
            cleaned = clean_for_tts(raw_text)
            self.assertNotIn("**", cleaned)
            self.assertNotIn("https://", cleaned)
            self.assertNotIn("`", cleaned)
            self.assertNotIn("🚀", cleaned)
            self.assertIn("Hola Cristian", cleaned)
            self.assertIn("Confirmado", cleaned)

            # 2. Probar interpolación lineal de vectores de voz (Voice Blending)
            voice_a = np.ones((512,), dtype=np.float32) * 1.0
            voice_b = np.ones((512,), dtype=np.float32) * 3.0
            blended = blend_voices(voice_a, voice_b, weight_a=0.7)
            
            # (1.0 * 0.7) + (3.0 * 0.3) = 0.7 + 0.9 = 1.6
            np.testing.assert_allclose(blended, np.ones((512,)) * 1.6, atol=1e-5)
        finally:
            if scripts_dir in sys.path:
                sys.path.remove(scripts_dir)

if __name__ == "__main__":
    unittest.main()
