# 🎙️ Realtime Voice Assistant Local — Conversacional en Tiempo Real (100% Offline)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Faster-Whisper CUDA](https://img.shields.io/badge/Faster--Whisper-CUDA-76B900.svg)](https://github.com/SYSTRAN/faster-whisper)
[![Ollama](https://img.shields.io/badge/Ollama-Llama_3.2_3B-black.svg)](https://ollama.com/)
[![Kokoro ONNX](https://img.shields.io/badge/Kokoro--TTS-82M_ONNX-FF6F00.svg)](https://github.com/thewh1teagle/kokoro-onnx)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Un asistente de voz full-duplex en tiempo real (similar a **ChatGPT Voice Mode**), diseñado para funcionar **100% local, sin conexión a internet, sin pagar APIs y optimizado para GPUs NVIDIA RTX de 6 GB VRAM** (como RTX 4050 / RTX 4060 Laptop).

Permite mantener llamadas de voz continuas con **manos libres**, transcripción en pantalla palabra por palabra, interrupciones instantáneas (**barge-in**), sincronización exacta de turnos y soporte bilingüe nativo con pronunciación natural en español e inglés.

---

## ⚡ Características Principales

* 📞 **Modo Llamada Manos Libres (*Full-Duplex*):** Habla con naturalidad sin tocar ningún botón. El VAD (*Voice Activity Detection*) calibrado a 650 ms detecta pausas naturales y procesa tu intervención al instante.
* 🎚️ **Filtro Anti-Respiración y Ruido Ambiental:** Control de sensibilidad ajustable en interfaz (Baja, Media, Alta) con indicador visual de umbral en tiempo real para evitar que respiraciones o ventiladores de laptop activen el micrófono por error.
* ⚡ **Transcripción Parcial en Vivo (*Live Streaming STT*):** Las palabras que dices se proyectan en pantalla en tiempo real con una latencia de apenas **~26 ms** gracias a Faster-Whisper en GPU CUDA.
* 💾 **Memoria Persistente Local (SQLite):** Historial completo de conversaciones, sesiones, traducciones y métricas guardadas automáticamente en `voice_assistant.db` sin enviar ningún dato a la nube.
* 🧠 **RAG Contextual y Memoria a Largo Plazo:** Inyección automática de notas y vocabulario previo en el contexto del modelo, permitiendo que la IA recuerde datos entre distintas sesiones y responda preguntas sobre notas pasadas.
* 🔧 **Tool Calling por Voz con Latencia Cero:** Ejecución directa y respuesta por voz instantánea (< 250 ms TTFA sin esperar al LLM):
  * 🕒 *Hora y fecha:* `"¿Qué hora es?"`, `"What time is it?"`
  * 📌 *Guardar notas:* `"Toma nota de comprar café"`, `"Recuérdame llamar al médico"`, `"Take a note to buy headphones"`
  * 📋 *Leer notas:* `"¿Cuáles son mis notas?"`, `"Léeme mis notas"`, `"Show my notes"`
  * 📝 *Vocabulario aprendido:* `"¿Qué vocabulario tengo?"`, `"What vocabulary did I learn?"`
* ⏹️ **Interrupciones Naturales (*Barge-in*):** Si la IA está hablando y comienzas a hablar, el audio se corta inmediatamente (<50 ms) y se cancela la tarea en el servidor, liberando recursos.
* 🇪🇸 **Fonética Nativa en Español (Sin acento extranjero):**
  * Integración de fonemizador G2P en español (`lang="es"`), logrando vocales puras, hache muda y cadencia nativa.
  * Selector dinámico entre voces nativas: 🇪🇸 **Dora** (`ef_dora` - cálida y conversacional) y 🇪🇸 **Alex** (`em_alex` - claro y enérgico).
* 🇺🇸 **Modo Práctica de Inglés (Tutor Inteligente):**
  * Conversación fluida con voces nativas 🇺🇸 **Sarah** (`af_sarah`) o 🇺🇸 **Adam** (`am_adam`).
  * Subtítulos traducidos al español y retroalimentación pedagógica sobre gramática/vocabulario en tiempo real.
* 🌐 **Modo Bilingüe Automático:** Detección automática del idioma hablado en cada turno para responder en la misma lengua.
* 🛡️ **Sanitización Dinámica de Texto para TTS:** Limpieza previa de emojis y acciones entre asteriscos (evita que el motor pronuncie *"asterisco sonríe asterisco"* o *"mano saludando"*).
* 🔄 **Sincronización Multi-Turno (`turn_id`):** Cada intervención lleva un ID unívoco, eliminando desfases en las traducciones o colisiones de audio.
* 🚀 **Streaming Continuo sin Frenos (Precarga de Audio):**
  * Motor Kokoro ONNX acelerado con **6 hilos en CPU** (~450 ms por frase completa).
  * Encadenamiento fluido con precarga en el navegador: cada oración subsiguiente llega con más de **2.5 segundos de anticipación**, logrando un habla continua sin baches ni silencios artificiales.

---

## 🏗️ Arquitectura y Distribución de Hardware

Diseñado para aprovechar al máximo una laptop o PC con **6 GB de VRAM**:

| Componente | Modelo / Tecnología | Dispositivo | VRAM / RAM | Latencia Típica |
| :--- | :--- | :--- | :--- | :--- |
| **STT (Audio a Texto)** | Faster-Whisper Multilingual (`base`) | GPU (CUDA fp16) | ~800 MB VRAM | **~26 ms** |
| **LLM (Cerebro)** | Ollama (`llama3.2:3b` - Q4_K_M) | GPU (CUDA - Keep-Alive) | ~2.2 GB VRAM | **~51 tokens/s** |
| **TTS (Texto a Voz)** | Kokoro-82M ONNX (6 hilos paralelos) | CPU (Multi-hilo) | 0 MB VRAM (~320 MB RAM) | **~450 ms / oración** |
| **VAD & Audio Engine** | Web Audio API + AudioContext | Navegador (Cliente) | N/A | **< 10 ms** |
| **Orquestador** | FastAPI + WebSockets Asíncronos | CPU | ~120 MB RAM | **< 5 ms** |
| **Memoria Persistente** | SQLite 3 (`database.py`) | Disco Local (Zero Overhead) | < 1 MB | **< 1 ms** |
| **Tool Calling Local** | Regex Intent Dispatcher (`tools.py`) | CPU | < 5 MB RAM | **< 1 ms (TTFA ~220 ms)** |
| **Total en Uso** | — | **GPU + CPU** | **~3.2 GB / 6 GB VRAM** | **TTFA: ~1.1s – 1.4s** |

---

## 📋 Requisitos Previos

1. **Sistema Operativo:** Windows 10/11 o Linux.
2. **GPU Recomendada:** NVIDIA RTX con al menos 4 GB – 6 GB VRAM (RTX 3050, 3060, 4050, 4060 o superior) con soporte CUDA.
3. **Python:** 3.10 o 3.11.
4. **Ollama:** Descárgalo desde [ollama.com](https://ollama.com) y descarga el modelo Llama 3.2:
   ```bash
   ollama pull llama3.2:3b
   ```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el Repositorio
```bash
git clone https://github.com/cristianhar/realtime-voice-assistant-local.git
cd realtime-voice-assistant-local
```

### 2. Crear y Activar Entorno Virtual
```bash
python -m venv venv

# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# En Windows (CMD):
.\venv\Scripts\activate.bat
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

*(Opcional para aceleración CUDA en Windows)*:
```bash
pip install nvidia-cublas-cu12 nvidia-cuda-nvrtc-cu12
```

### 4. Descargar Modelos de Síntesis Kokoro
Coloca los archivos del modelo en la carpeta `models/`:
* [kokoro-v0_19.onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v0_19.onnx) (~310 MB)
* [voices-v1.0.bin](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin) (~28 MB)

*(Puedes descargarlos fácilmente desde PowerShell):*
```powershell
Invoke-WebRequest -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v0_19.onnx" -OutFile "models/kokoro-v0_19.onnx"
Invoke-WebRequest -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" -OutFile "models/voices-v1.0.bin"
```

---

## 🎮 Ejecución

### Opción Rápida (1 solo clic en Windows)
Haz doble clic en:
```bash
run.bat
```
El script levantará Ollama, iniciará el servidor FastAPI y abrirá tu navegador en `http://127.0.0.1:8000`.

### Opción Manual desde Terminal
```bash
# 1. Asegúrate de tener Ollama activo
ollama serve

# 2. Inicia el servidor
python server.py

# 3. Abre en tu navegador
http://127.0.0.1:8000
```

---

## 💡 Guía de Uso de la Interfaz (Web UI)

Al abrir `http://127.0.0.1:8000`, dispondrás de una interfaz moderna y lista para conversar:

1. **Selección de Modo (Barra Superior):**
   * **🇺🇸 Practicar Inglés:** Actúa como tutor de inglés nativo. Corrige errores comunes de forma amigable, muestra lo que dijiste en inglés, su traducción al español y una tarjeta con tips gramaticales en el panel derecho.
   * **🇪🇸 Español:** Asistente conversacional nativo en español con voz cálida o dinámica (Dora o Alex).
   * **🌐 Bilingüe / Auto:** Detecta automáticamente en qué idioma le hablas en cada turno y responde en el mismo.
2. **Modo Llamada Manos Libres (📞 Iniciar Modo Llamada):**
   * Haz clic una vez para activar la llamada continua.
   * Puedes hablar con total naturalidad; el sistema detecta cuándo terminas de hablar mediante el VAD, transcribe en tiempo real y te responde en voz alta.
   * Si la IA está hablando y deseas interrumpirla, simplemente empieza a hablar o presiona **⏹ Interrumpir**.
3. **Calibración del Filtro VAD (Anti-Respiración):**
   * Observa la barra verde de nivel de voz: verás una **línea vertical roja**.
   * Tu respiración o el ventilador deben quedarse a la izquierda de la línea roja. Solo cuando hablas, la barra verde cruza la línea roja.
   * Puedes ajustar el selector entre **Baja**, **Media** o **Alta** según la sensibilidad de tu micrófono.
4. **Selector de Voz de IA:**
   * Cambia en cualquier momento entre 🇪🇸 **Dora** (Femenina), 🇪🇸 **Alex** (Masculino), 🇺🇸 **Sarah** (Femenina) y 🇺🇸 **Adam** (Masculino).

---

## ⚡ Optimización para Laptops NVIDIA (Desbloqueo de Relojes P0)

En portátiles con GPU NVIDIA (ej. MSI Thin 15, Lenovo Legion, ASUS TUF), Windows puede limitar la GPU a estados de bajo consumo (P4/P5) con frecuencias de memoria reducidas (5,501 MHz en lugar de los 8,001 MHz de GDDR6).

Incluimos scripts listos para desbloquear el máximo rendimiento:

1. **Desbloquear:** Haz clic derecho en `optimizar_gpu.bat` (o ejecuta `optimizar_gpu.ps1`) $\rightarrow$ **Ejecutar como Administrador**.
   * Fija el reloj de memoria a **8,001 MHz**.
   * Activa el estado **P0** (Max Performance).
   * Eleva la velocidad de inferencia de Ollama a más de **50 tokens/s**.
2. **Restaurar:** Si deseas volver a los valores estándar de fábrica con ahorro de energía, ejecuta `restaurar_gpu.bat`.

---

## 🧪 Pruebas Automatizadas y Benchmarks

Dentro de la carpeta `tests/` se incluyen suites completas para medir rendimiento, continuidad de voz y latencias:

```bash
# Evaluación de continuidad, medición de silencios/frenos y barge-in
python tests/test_benchmark_continuity.py

# Prueba integral de flujo conversacional y WebSocket
python tests/test_spanish_voice_flow.py

# Benchmark completo de componentes (STT, LLM TTFT, Kokoro TTS)
python tests/run_benchmarks.py

# Simulación de conversaciones multi-turno e interrupciones
python tests/benchmark_simulation_suite.py
```

---

## ⏱️ Métricas de Rendimiento Reales (Medidas en RTX 4050 Laptop)

| Métrica | Tiempo Medido | Evaluación |
| :--- | :--- | :--- |
| **Detección de Fin de Frase (Silencio VAD)** | `650 ms` | Natural y no intrusivo |
| **Transcripción STT (Faster-Whisper CUDA)** | **`26.2 ms`** ⚡ | Tiempo real instantáneo |
| **Tiempo al Primer Token LLM (TTFT)** | **`180 – 320 ms`** | Inferencia continua en VRAM |
| **Síntesis Oración Completa (Kokoro ONNX 6 hilos)** | **`~450 ms`** | 4x más rápido que configuración estándar |
| **Latencia al Primer Audio (TTFA)** | **`~1.1 – 1.4 s`** 🚀 | Comparable a ChatGPT Voice |
| **Colchón de Buffer Entre Oraciones** | **`+2,842 ms`** | **0% pausas / 0 frenos audibles** |
| **Velocidad de Generación LLM (Llama 3.2 3B)** | **`~51.5 tokens/s`** | Máximo ancho de banda GPU P0 |

---

## 🗺️ Roadmap de Desarrollo

### Fase 5 (Completada): Memoria Persistente y Herramientas (Tool Calling)
* [x] **Persistencia Local en SQLite (`database.py`):** Almacenamiento local de conversaciones, historial de sesiones, notas y vocabulario en `voice_assistant.db` sin requerir nube.
* [x] **RAG Ultraligero y Memoria Contextual:** Inyección automática de notas y vocabulario en el prompt del sistema (`get_memory_context_string()`).
* [x] **Tool Calling Local con Latencia Cero (`tools.py`):** Ejecución instantánea (< 250 ms) para consultar hora/fecha, tomar notas por voz, listar notas y consultar vocabulario.
* [x] **Panel Visual de Notas Rápidas por Voz:** Componente interactivo en el dashboard con actualización en tiempo real y botón de purga.

### Fase 6 (Próximas Mejoras):
* [ ] **Búsqueda Semántica Vectorial (`sqlite-vec` / ChromaDB):** Memoria densa basada en similitud de cosenos para recuerdos a largo plazo.
* [ ] **Automatizaciones del Sistema Operativo:** Capacidad para abrir aplicaciones locales, controlar volumen o reproducir música mediante comandos de voz.
* [ ] **Exportación de Sesiones:** Generación de resúmenes de estudio y notas en formato Markdown o PDF.

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más detalles.
