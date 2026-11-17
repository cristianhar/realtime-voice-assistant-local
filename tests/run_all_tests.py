import unittest
import sys
import os
import time

# Asegurar que la raíz del proyecto esté en sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.utils import configure_utf8_stdio
configure_utf8_stdio()

def run_all_e2e_and_unit_tests():
    print("=" * 70)
    print("  EJECUTANDO SUITE COMPLETA DE PRUEBAS END-TO-END Y UNITARIAS")
    print("=" * 70)

    # Aislar la base de datos para pruebas y proteger la base de datos real voice_assistant.db
    test_db_path = os.path.join(PROJECT_ROOT, "test_voice_assistant.db")
    os.environ["VOICE_ASSISTANT_DB_PATH"] = test_db_path

    import database
    database.init_db()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Módulos de pruebas
    test_modules = [
        "tests.test_chunker",
        "tests.test_sanitization",
        "tests.test_tools_memory",
        "tests.test_e2e_pipeline",
        "tests.test_agensi_skills_e2e",
        "tests.test_humanization_and_vad",
        "tests.test_custom_tools_and_personas",
        "tests.test_ui_redesign",
        "tests.test_conversation_history",
        "tests.test_synchronization_and_timing"
    ]

    if "--with-audio" in sys.argv or "--all" in sys.argv:
        test_modules.append("tests.test_live_models_e2e")
        print("🔊 Modo de audio real activado (--with-audio): incluye test de síntesis Kokoro y STT CUDA.")

    for mod in test_modules:
        try:
            suite.addTests(loader.loadTestsFromName(mod))
            print(f"[OK] Modulo cargado: {mod}")
        except Exception as e:
            print(f"[ERROR] Error cargando {mod}: {e}")

    print("-" * 70)
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    try:
        result = runner.run(suite)
    finally:
        # Limpieza de base de datos de prueba
        if "VOICE_ASSISTANT_DB_PATH" in os.environ:
            del os.environ["VOICE_ASSISTANT_DB_PATH"]
        for ext in ["", "-wal", "-shm"]:
            fpath = test_db_path + ext
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    duration = time.time() - start_time

    print("=" * 70)
    print(f"  RESUMEN FINAL DE PRUEBAS:")
    print(f"  Total pruebas ejecutadas: {result.testsRun}")
    print(f"  Aprobadas: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Fallos: {len(result.failures)}")
    print(f"  Errores: {len(result.errors)}")
    print(f"  Tiempo total: {duration:.3f} segundos")
    print("=" * 70)

    if not result.wasSuccessful():
        print("[FALLO] Hay pruebas que no pasaron. Revisa los errores antes de hacer commit.")
        sys.exit(1)
    else:
        print("[EXITO] Todas las pruebas End-to-End y unitarias pasaron con exito.")
        sys.exit(0)

if __name__ == "__main__":
    run_all_e2e_and_unit_tests()
