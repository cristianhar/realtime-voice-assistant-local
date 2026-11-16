---
name: voice-e2e-quality-gate
description: >-
  Quality gate and automated End-to-End test runner for the Realtime Local Voice Assistant.
  Runs comprehensive verification across SQLite memory, local tool calling, audio chunking,
  text sanitization, and full conversational pipeline before any release or Git push.
---

# 🛡️ Voice Assistant E2E Quality Gate & Test Runner

Esta skill proporciona las directrices y el protocolo automatizado de pruebas End-to-End para garantizar que ninguna implementación, refactorización o cambio de código se suba al repositorio sin haber sido validado rigurosamente.

---

## 📋 Protocolo de Verificación Obligatorio

Antes de realizar cualquier commit o push a `main`, ejecuta siempre la suite unificada:

```powershell
python tests/run_all_tests.py
```

### Qué valida la suite:
1. **`test_chunker.py` (5 tests):**
   * División limpia de oraciones completas (`.`, `!`, `?`, `\n`).
   * Prevención de cortes en comas cortas (`"Sí,"` o `"Well,"`) para evitar frenos de audio.
   * Manejo de cláusulas largas y desbordamiento de buffer sin signos de puntuación.
2. **`test_sanitization.py` (5 tests):**
   * Eliminación de asteriscos narrativos (`*sonríe*`, `*laughs*`).
   * Eliminación de paréntesis de rol y emojis visuales.
   * Preservación de signos ortográficos en español (`¿`, `¡`, acentos, diéresis).
   * Detección heurística de idioma (Español vs. Inglés).
3. **`test_tools_memory.py` (10 tests):**
   * Tool Calling de hora en español e inglés.
   * Tool Calling de guardado de notas de voz.
   * Tool Calling de listado de notas recientes.
   * Tool Calling de listado de vocabulario practicado.
   * Generación del bloque de memoria persistente para el LLM.
   * Ciclo completo de persistencia SQLite (`sessions`, `messages`, `vocabulary`, `notes`).
4. **`test_e2e_pipeline.py` (5 tests):**
   * Ciclo de vida completo de sesión multi-turno.
   * Inyección contextual en el prompt del sistema (`PROMPTS[mode] + memory`).
   * Simulación de streaming de tokens y división continua en oraciones fluidas.
   * Sanitización de texto para Kokoro TTS.

---

## ⚡ Verificación de Rendimiento de GPU (CUDA)

Para asegurar que la GPU NVIDIA esté en estado **P0** (máximo ancho de banda de VRAM):

```powershell
# Ejecutar como Administrador en PowerShell:
powershell -ExecutionPolicy Bypass -File .\optimizar_gpu.ps1
```

Verificar que:
* El reloj de memoria GDDR6 esté fijado en **8,001 MHz**.
* El estado de energía sea **P0**.
* Ollama esté respondiendo a **>50 tokens/s**.

---

## 🚀 Criterio de Aprobación para Commits (Quality Gate)
* **Regla 1:** Los 25 tests de `tests/run_all_tests.py` deben terminar en estado `OK` (0 fallos, 0 errores).
* **Regla 2:** Si se modificó la lógica de WebSocket o streaming, verificar que `server.py` arranque limpiamente.
* **Regla 3:** Nunca commitear archivos binarios pesados (`.onnx`, `.bin`, `.db`, `.wav`).
