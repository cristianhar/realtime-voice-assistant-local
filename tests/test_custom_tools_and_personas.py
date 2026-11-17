"""
test_custom_tools_and_personas.py - Test Suite for Custom Tools Engine, Persona Hub, and 1-Line Installers.
"""
import unittest
import os
import sys
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.plugin_loader import load_custom_tools, dispatch_custom_tool, get_loaded_tools_metadata

class TestCustomToolsAndPersonas(unittest.TestCase):

    def setUp(self):
        load_custom_tools()

    def test_01_plugin_loader_auto_discovery(self):
        """Valida que el motor de plugins descubra automáticamente herramientas en custom_tools/."""
        metadata = get_loaded_tools_metadata()
        tool_names = [m["name"] for m in metadata]

        self.assertIn("dice_roller", tool_names, "No se encontró el plugin dice_roller")
        self.assertIn("dev_quote", tool_names, "No se encontró el plugin dev_quote")

        for m in metadata:
            self.assertTrue(len(m["triggers"]) > 0, f"El plugin {m['name']} debe tener al menos un trigger.")
            self.assertIsNotNone(m["description"], f"Falta descripción en {m['name']}.")

    def test_02_dice_roller_execution(self):
        """Valida la ejecución del plugin dice_roller por voz (dados y monedas)."""
        # 1. Tirada de dados en español
        handled_dice_es, res_dice_es, tool_id = dispatch_custom_tool("oye tira un dado por favor", lang="es")
        self.assertTrue(handled_dice_es)
        self.assertEqual(tool_id, "dice_roller")
        self.assertIn("Tirando un dado", res_dice_es)

        # 2. Tirada de moneda en español
        handled_coin_es, res_coin_es, _ = dispatch_custom_tool("lanza una moneda a ver qué sale", lang="es")
        self.assertTrue(handled_coin_es)
        self.assertIn("Lanzando la moneda", res_coin_es)

        # 3. Tirada de moneda en inglés
        handled_coin_en, res_coin_en, _ = dispatch_custom_tool("flip a coin for me", lang="en")
        self.assertTrue(handled_coin_en)
        self.assertIn("Flipping the coin", res_coin_en)

    def test_03_dev_quote_execution(self):
        """Valida la ejecución del plugin dev_quote."""
        handled_quote_es, res_quote_es, tool_id = dispatch_custom_tool("dime una frase de programación", lang="es")
        self.assertTrue(handled_quote_es)
        self.assertEqual(tool_id, "dev_quote")
        self.assertTrue(len(res_quote_es) > 10)

        handled_quote_en, res_quote_en, _ = dispatch_custom_tool("give me a coding quote", lang="en")
        self.assertTrue(handled_quote_en)
        self.assertTrue(len(res_quote_en) > 10)

    def test_04_personas_json_schemas(self):
        """Verifica la existencia y validez estructural de todos los perfiles en personas/."""
        personas_dir = os.path.join(PROJECT_ROOT, "personas")
        self.assertTrue(os.path.isdir(personas_dir), "No existe la carpeta personas/")

        required_personas = ["jarvis.json", "english_tutor.json", "senior_tech_lead.json", "zen_coach.json"]
        found_files = [f for f in os.listdir(personas_dir) if f.endswith(".json")]

        for req in required_personas:
            self.assertIn(req, found_files, f"Falta el archivo de persona {req}")

        for fname in found_files:
            fpath = os.path.join(personas_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            for key in ["id", "name", "voice_name", "system_prompt", "speech_speed"]:
                self.assertIn(key, data, f"En {fname} falta la propiedad obligatoria '{key}'.")
            self.assertGreater(len(data["system_prompt"]), 20, f"System prompt muy corto en {fname}.")

    def test_05_installer_scripts_integrity(self):
        """Verifica la sintaxis e integridad de los instaladores universales de 1 línea."""
        # 1. install.ps1 (Windows)
        ps1_path = os.path.join(PROJECT_ROOT, "install.ps1")
        self.assertTrue(os.path.isfile(ps1_path), "Falta install.ps1")
        with open(ps1_path, "r", encoding="utf-8") as f:
            ps1_content = f.read()
        self.assertIn("Python", ps1_content)
        self.assertIn("requirements.txt", ps1_content)
        self.assertIn("launch_voice_assistant.bat", ps1_content)

        # 2. install.sh (Linux/macOS)
        sh_path = os.path.join(PROJECT_ROOT, "install.sh")
        self.assertTrue(os.path.isfile(sh_path), "Falta install.sh")
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_content = f.read()
        self.assertTrue(sh_content.startswith("#!/usr/bin/env bash") or sh_content.startswith("#!/bin/bash"))
        self.assertIn("server.py", sh_content)

    def test_06_community_files_integrity(self):
        """Verifica presencia de archivos estándar de comunidad GitHub."""
        contrib_path = os.path.join(PROJECT_ROOT, "CONTRIBUTING.md")
        self.assertTrue(os.path.isfile(contrib_path), "Falta CONTRIBUTING.md")

        bug_tpl = os.path.join(PROJECT_ROOT, ".github", "ISSUE_TEMPLATE", "bug_report.md")
        self.assertTrue(os.path.isfile(bug_tpl), "Falta bug_report.md")

        feat_tpl = os.path.join(PROJECT_ROOT, ".github", "ISSUE_TEMPLATE", "feature_request.md")
        self.assertTrue(os.path.isfile(feat_tpl), "Falta feature_request.md")

        rel_notes = os.path.join(PROJECT_ROOT, "docs", "RELEASE_NOTES_v1.0.0.md")
        self.assertTrue(os.path.isfile(rel_notes), "Falta docs/RELEASE_NOTES_v1.0.0.md")

if __name__ == "__main__":
    unittest.main()

