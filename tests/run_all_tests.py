import unittest
import sys
import os
import time

# Asegurar que la raíz del proyecto esté en sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_all_e2e_and_unit_tests():
    print("=" * 70)
    print("  EJECUTANDO SUITE COMPLETA DE PRUEBAS END-TO-END Y UNITARIAS")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Módulos de pruebas
    test_modules = [
        "tests.test_chunker",
        "tests.test_sanitization",
        "tests.test_tools_memory",
        "tests.test_e2e_pipeline"
    ]

    if "--with-audio" in sys.argv or "--all" in sys.argv:
        test_modules.append("tests.test_live_models_e2e")
        print("🔊 Modo de audio real activado (--with-audio): incluye test de síntesis Kokoro y STT CUDA.")

    for mod in test_modules:
        try:
            suite.addTests(loader.loadTestsFromName(mod))
            print(f"✓ Módulo cargado: {mod}")
        except Exception as e:
            print(f"✗ Error cargando {mod}: {e}")

    print("-" * 70)
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
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
        print("❌ FALLO: Hay pruebas que no pasaron. Revisa los errores antes de hacer commit.")
        sys.exit(1)
    else:
        print("✅ ÉXITO TOTAL: Todas las pruebas End-to-End y unitarias pasaron con éxito.")
        sys.exit(0)

if __name__ == "__main__":
    run_all_e2e_and_unit_tests()
