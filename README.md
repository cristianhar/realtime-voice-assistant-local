# 🎙️ Realtime Voice Assistant Local — Conversacional en Tiempo Real (100% Offline)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](https://www.docker.com/)
[![Faster-Whisper CUDA](https://img.shields.io/badge/Faster--Whisper-CUDA-76B900.svg)](https://github.com/SYSTRAN/faster-whisper)
[![Ollama](https://img.shields.io/badge/Ollama-Llama_3.2_3B-black.svg)](https://ollama.com/)
[![Kokoro ONNX](https://img.shields.io/badge/Kokoro--TTS-82M_ONNX-FF6F00.svg)](https://github.com/thewh1teagle/kokoro-onnx)
[![PWA](https://img.shields.io/badge/PWA-Mobile_Ready-purple.svg)](https://web.dev/progressive-web-apps/)
[![Tests Passing](https://img.shields.io/badge/Quality_Gate-38%2F38_Passing-brightgreen.svg)](tests/run_all_tests.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Un asistente de voz full-duplex en tiempo real (similar a **ChatGPT Voice Mode**), diseñado para funcionar **100% local, privado, sin conexión a internet y optimizado para GPUs NVIDIA RTX de 6 GB VRAM** (como RTX 4050 / RTX 4060 Laptop o superiores).

Permite mantener llamadas de voz continuas con **manos libres**, transcripción instantánea palabra por palabra, interrupciones al vuelo (**barge-in**), memoria semántica densa (Hybrid RAG), mezclas de voces interpoladas en tiempo real (**Voice Blends**), modo susurro (**Whisper Mode**), soporte para móviles vía **HTTPS / PWA** y despliegue rápido con **Docker & Docker Compose**.

---

## 🏗️ Diagrama de Arquitectura End-to-End

```mermaid
flowchart LR
    subgraph Cliente ["💻 / 📱 Cliente (PC / Móvil PWA)"]
        MIC["🎙️ Micrófono (16kHz PCM)"] --> VAD["🎚️ Web Audio VAD + Filtro Ruido"]
        VAD --> WS_CLIENT["⚡ WebSocket Seguro (WSS)"]
        WS_CLIENT -. Interrupción Barge-in .-> CANCEL["⏹️ Detención Inmediata (<50ms)"]
        WS_AUDIO["🔊 Web Audio Streaming Buffer"] <-- Audio Base64 Chunks -- WS_CLIENT
    end

    subgraph Servidor ["🖥️ Servidor Local FastAPI (server.py)"]
        WS_CLIENT --> ORCH["🎯 Orquestador de Turnos (turn_id)"]
        ORCH --> DISPATCHER{"🔧 Tool Dispatcher<br/>(Regex Intent)"}
        
        DISPATCHER -- Tool Coincide --> TOOLS["⚡ Zero-Latency Tools<br/>Hora | Apps | GPU | Notas (<1ms)"]
        DISPATCHER -- No Tool --> STT["🎧 Faster-Whisper CUDA<br/>STT Parcial (~26ms)"]
        
        STT --> RAG["🧠 Hybrid RAG Memory<br/>3072D Cosine + FTS5 SQLite"]
        RAG --> LLM["🦙 Ollama LLaMA 3.2 3B<br/>Streaming (~51 tps, Keep-Alive)"]
        
        LLM --> CHUNKER["✂️ SentenceChunker<br/>(División Gapless de oraciones)"]
        TOOLS --> CHUNKER
        
        CHUNKER --> TTS["🗣️ Kokoro ONNX (6 hilos CPU)<br/>Voice Blends (RTF 0.27x)<br/>Modo Susurro (-52.6% RMS)"]
        TTS --> WS_CLIENT
    end

    subgraph Persistencia ["💾 Capa de Persistencia (database.py)"]
        RAG <--> DB[("SQLite 3<br/>voice_assistant.db")]
        TOOLS -. Indexación Asíncrona Daemon .-> DB
    end
```

---

## ⚡ Características Principales

### 1. 📞 Modo Llamada Manos Libres (*Full-Duplex*) & Barge-in
* **VAD Calibrado a 650 ms:** Detecta pausas naturales al hablar sin necesidad de pulsar botones.
* **Interrupción Inmediata (*Barge-in*):** Si la IA está hablando y comienzas a hablar, el audio se silencia instantáneamente (<50 ms), cancelando la generación y liberando recursos.
* **Filtro Anti-Respiración y Ruido Ambiental:** Umbral dinámico visual en tiempo real para evitar que suspiros o ventiladores activen el micrófono por error.

### 2. 🧠 Memoria Semántica Densa (Hybrid RAG: 3072D + FTS5)
* **Similitud de Coseno en Memoria Local:** Vectores densos de 3072 dimensiones generados con Ollama y cacheados en SQLite (`embeddings_cache`) para recuperar conceptos aunque las palabras exactas no coincidan.
* **Búsqueda Léxica FTS5:** Indexación de texto completo ultrarrápida (`notes_fts`, `messages_fts`).
* **Perfil Persistente de Usuario:** Inyección automática de contexto personalizado (**Cristian Arboleda**, nivel de inglés, intereses técnicos).

### 3. 🔧 Herramientas Locales Zero-Latency con Indexación Asíncrona
* **Ejecución Instantánea (< 1 ms a 11 ms):**
  * 🕒 *Hora y fecha exacta:* `"¿Qué hora es?"`, `"What time is it?"` (`0.38 ms`)
  * ⚡ *Estado de Hardware / GPU NVIDIA:* `"¿Cómo está la GPU?"`, `"Hardware status"` (`47 ms` vía `nvidia-smi`)
  * 🚀 *Lanzamiento de Aplicaciones del SO:* `"Abre la calculadora"`, `"Abre Visual Studio Code"`, `"Abre Spotify"`, `"Abre YouTube"`, `"Abre GitHub"`, `"Abre el navegador"`.
  * 📌 *Guardar notas por voz:* `"Toma nota de comprar café y pan"` (**`11 ms`**, 300x más rápido gracias a indexación en segundo plano).
  * 📋 *Consultar notas:* `"¿Cuáles son mis notas?"`, `"Show my notes"` (`1.5 ms`).
  * 📝 *Vocabulario practicado:* `"¿Qué vocabulario tengo?"`, `"What words did I learn?"` (`1.2 ms`).
  * 🌐 *Búsqueda Web en Tiempo Real:* `"Busca en internet el clima en Medellín"`, `"What is quantum computing according to Wikipedia"` (`80 ms – 200 ms`).
  * ⏩ *Control Dinámico de Velocidad:* `"Habla más rápido"`, `"Habla más despacio"`, `"Velocidad normal"` (ajuste instantáneo pitch-preserved `0.85x` – `1.25x`).

### 4. 🎭 Voice Blending Híbrido & Modo Susurro (Whisper Mode)
* **Mezcla Híbrida de Voces (Voice Blends):**
  * `blend_dora_sarah`: 60% Dora (Español) + 40% Sarah (Inglés) $\rightarrow$ **RTF 0.27x (3.7x más rápido que tiempo real)**.
  * `blend_alex_adam`: 60% Alex (Español) + 40% Adam (Inglés) $\rightarrow$ **RTF 0.27x**.
* **Modo Susurro Acústico (Whisper Mode):**
  * Atenuación de amplitud modulada al **52.6%** del RMS original.
  * Cadencia ralentizada con pausas suaves para un tono relajante y confidencial.

### 5. 🎵 Feedback Acústico Sintético (Earcons) & Control Dinámico de Velocidad
* **Earcons Sintéticos con Web Audio API (`static/js/earcons.js`):**
  * Generación de tonos matemáticos en tiempo real mediante `OscillatorNode` y `GainNode` con cero latencia de carga y 0 bytes transferidos.
  * *Inicio de llamada:* Arpegio ascendente Do5 $\rightarrow$ Mi5 $\rightarrow$ Sol5 (523 Hz – 784 Hz).
  * *Fin de llamada:* Arpegio descendente Sol5 $\rightarrow$ Mi5 $\rightarrow$ Do5 (784 Hz – 523 Hz).
  * *Barge-in / Interrupción:* Clic suave de baja frecuencia (280 Hz $\rightarrow$ 140 Hz).
  * *Éxito de herramienta (Tool Calling):* Doble ping armónico La5 $\rightarrow$ Do6 (880 Hz – 1046 Hz).
* **Control de Velocidad del Habla (0.85x a 1.25x):**
  * Selector visual en la barra de controles (`0.85x`, `1.0x`, `1.15x`, `1.25x`).
  * Control por voz integrado: di *"habla más rápido"*, *"habla más despacio"*, o *"speak faster"* y el asistente ajusta su tasa de reproducción instantáneamente sin distorsión tonal.

### 6. 💼 Personalidades Dinámicas & Modo "Mock Interviewer" (Técnico / IELTS)
* **5 Personalidades Especializadas:**
  * 🎓 *Language Coach:* Correcciones gramaticales y vocabulario guiado.
  * 🤗 *Casual Friend:* Conversación empática, informal y cercana.
  * 💻 *Senior Tech Lead:* Discusiones de arquitectura de software, patrones y buenas prácticas.
  * 👔 *Executive Mentor:* Liderazgo, asertividad y toma de decisiones de alto impacto.
  * 💼 *Tech & IELTS Interviewer:* Simulador de entrevistas técnicas de ingeniería de software (FAANG/Big Tech) y evaluador de fluidez para exámenes IELTS/TOEFL con feedback constructivo tras cada intervención.

### 7. 🌐 Búsqueda Web en Tiempo Real Tri-Engine (100% Gratuita, Sin API Keys)
* **Arquitectura de Búsqueda Híbrida (`tools.py`):**
  * 🌦️ *Clima Local Instantáneo (wttr.in):* Respuesta en ~80 ms en texto plano.
  * 📚 *Wikipedia REST API:* Definición enciclopédica y conceptos en ~120 ms.
  * 🌐 *DuckDuckGo HTML Search:* Búsqueda web general en ~200 ms sin desafíos JS ni captchas.

### 8. 📱 Soporte Móvil First, HTTPS Seguro y PWA
* **Contexto Seguro HTTPS Automático:** Generación transparente de certificados SSL en `certs/` para que Chrome y Safari en Android/iOS permitan acceso al micrófono en red local (`https://192.168.x.x:8000`).
* **Progressive Web App (PWA):** Incluye `manifest.json` y `sw.js` (Service Worker) para instalar como aplicación nativa a pantalla completa en tu teléfono.

### 9. 🌐 Frontend Modular y Soporte Multiidioma (i18n)
* **8 Idiomas Internacionales:** Español (🇪🇸), Inglés (🇺🇸), Portugués (🇧🇷), Francés (🇫🇷), Alemán (🇩🇪), Italiano (🇮🇹), Japonés (🇯🇵) y Chino Simplificado (🇨🇳).
* **Arquitectura Frontend Desacoplada (`static/js/`):** Módulos independientes para audio player, grabador con VAD, UI de chat, cajón de notas, telemetría de GPU y sintetizador de earcons.
* **Exportación de Sesiones:** Descarga el historial conversacional completo en formato Markdown (📥).

---

## 🏗️ Distribución de Hardware y Consumo de Recursos

Diseñado y calibrado para una laptop o PC con **6 GB de VRAM** (Probado en NVIDIA GeForce RTX 4050 Laptop):

| Componente | Modelo / Motor | Dispositivo | VRAM / RAM | Latencia Típica |
| :--- | :--- | :--- | :--- | :--- |
| **STT (Audio a Texto)** | Faster-Whisper (`base`) | GPU (CUDA fp16) | ~800 MB VRAM | **~26 ms** |
| **LLM (Cerebro)** | Ollama (`llama3.2:3b` Q4_K_M) | GPU (CUDA Keep-Alive) | ~2.2 GB VRAM | **~51 tokens/s** |
| **TTS (Texto a Voz)** | Kokoro-82M ONNX (6 hilos) | CPU (Multi-hilo) | 0 MB VRAM (~320 MB RAM) | **~450 ms (RTF 0.27x)** |
| **Memoria RAG** | SQLite 3 + Vectores 3072D | Disco / Caché RAM | < 5 MB RAM | **< 5 ms** |
| **Herramientas Locales** | Dispatcher Regex + Background Threads | CPU | < 2 MB RAM | **0.18 – 11 ms** |
| **Total del Sistema** | — | **GPU + CPU** | **3.0 GB / 6 GB VRAM (50%)** | **TTFA: ~1.1s – 1.4s** |

---

## 🚀 Despliegue Rápido con Docker & Docker Compose

La forma más sencilla de ejecutar todo el stack sin configurar entornos de Python locales:

```bash
# 1. Clonar el repositorio
git clone https://github.com/cristianhar/realtime-voice-assistant-local.git
cd realtime-voice-assistant-local

# 2. Iniciar con Docker Compose (con soporte para GPU NVIDIA)
docker compose up --build
```

El orquestador de Docker:
1. Levanta el contenedor de **Ollama** con persistencia en `ollama_data`.
2. Descarga automáticamente el modelo **LLaMA 3.2 3B** en el primer arranque.
3. Levanta el contenedor de **Voice Assistant** con HTTPS en el puerto `8000`.

---

## 💻 Instalación y Ejecución Local Nativa (Windows / Linux)

### 1. Clonar el Repositorio
```bash
git clone https://github.com/cristianhar/realtime-voice-assistant-local.git
cd realtime-voice-assistant-local
```

### 2. Crear Entorno Virtual
```bash
python -m venv venv

# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# En Linux / macOS:
source venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

*(Para aceleración CUDA en Windows)*:
```bash
pip install nvidia-cublas-cu12 nvidia-cuda-nvrtc-cu12
```

### 4. Modelos Kokoro TTS
Coloca los archivos en la carpeta `models/`:
* [kokoro-v0_19.onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v0_19.onnx) (~310 MB)
* [voices-v1.0.bin](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin) (~28 MB)

*(Descarga en 1 línea con PowerShell):*
```powershell
Invoke-WebRequest -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v0_19.onnx" -OutFile "models/kokoro-v0_19.onnx"
Invoke-WebRequest -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" -OutFile "models/voices-v1.0.bin"
```

### 5. Iniciar Ollama y Descargar Modelo
```bash
ollama serve
ollama pull llama3.2:3b
```

### 6. Ejecutar el Servidor
```bash
# Modo estándar con HTTPS (recomendado para acceder desde PC y Celular):
python server.py --https --host 0.0.0.0 --port 8000
```

En consola verás las URLs de acceso directo:
* 💻 **En esta PC:** `https://localhost:8000`
* 📱 **En tu Celular:** `https://192.168.x.x:8000`

---

## 🧪 Pruebas Automatizadas y Calibración (Quality Gate)

El proyecto cuenta con un riguroso sistema de pruebas de calidad y pruebas de circuito cerrado en hardware real:

```bash
# 🚀 Ejecutar la suite completa (38 pruebas unitarias y E2E en ~3.5s):
python tests/run_all_tests.py

# 🔊 Ejecutar incluyendo prueba de audio real en hardware (Kokoro ONNX -> Faster-Whisper CUDA Loopback):
python tests/run_all_tests.py --all

# 🔬 Ejecutar la suite completa de Benchmark E2E y Calibración de Hardware en vivo por WebSocket:
python tests/benchmark_full_calibration_suite.py
```

### Resumen de Suites en `tests/`:
* `tests/test_e2e_pipeline.py`: Valida persistencia SQLite, tools locales, Hybrid RAG, chunker gapless y blends de voz.
* `tests/test_tools_memory.py`: Pruebas exhaustivas de intención y latencia de tools (hora, notas, vocabulario, apps, web search, speed control).
* `tests/test_chunker.py`: Verificación matemática del streaming continuo sin silencios artificiales.
* `tests/test_sanitization.py`: Sanitización de texto para síntesis limpia sin emojis ni asteriscos.
* `tests/test_live_models_e2e.py`: Prueba de circuito cerrado de audio real (síntesis de audio con Dora y transcripción con Faster-Whisper CUDA).
* `tests/benchmark_full_calibration_suite.py`: Telemetría en vivo por WebSocket de TTFT, TTFA, RTF y GPU clocks.

---

## ⏱️ Métricas de Rendimiento Reales (Calibradas en RTX 4050)

```text
==============================================================================
  Componente                Métrica Observada    Objetivo Calibración   Estado
==============================================================================
  Hora (Español)            0.38 ms              < 5 ms                 EXCELENTE
  Hora (Inglés)             0.18 ms              < 5 ms                 EXCELENTE
  Guardar Nota de Voz       11.27 ms             < 50 ms                300x MÁS RÁPIDO
  Listar Notas              1.50 ms              < 5 ms                 EXCELENTE
  Estado de Hardware GPU    47.66 ms             < 100 ms               EXCELENTE
  RAG Semántico (3072D)     4.50 ms              < 20 ms                CALIBRADO
  Kokoro Voice Blends       RTF 0.27x            < 0.35x                3.7x TIEMPO REAL
  Modo Susurro (Atenuación) 52.6% RMS            ~ 50%                  CALIBRADO
  TTFA Tool Calling (WSS)   1395.6 ms            < 1500 ms              EXCELENTE
  Interrupción (Barge-in)   Confirmado (<50ms)   Inmediato              APROBADO
==============================================================================
```

---

## 💻 Requisitos del Sistema

| Componente | Mínimo | Recomendado |
| :--- | :--- | :--- |
| **Sistema Operativo** | Windows 10/11 (64-bit) o Ubuntu 22.04+ LTS | Windows 11 o Ubuntu 24.04 (Nativo o Docker) |
| **GPU** | NVIDIA GTX 1650 / RTX 3050 (4 GB VRAM) | NVIDIA RTX 4050 / 4060 Laptop o Desktop (6 GB+ VRAM) |
| **Procesador (CPU)** | 4 núcleos x86_64 | 6+ núcleos (Intel Core i5/i7 o AMD Ryzen 5/7) |
| **Memoria RAM** | 8 GB | 16 GB |
| **CUDA Driver** | CUDA 12.x | CUDA 12.4+ / cuBLAS v12 |
| **Navegador** | Chrome 110+, Edge 110+, Safari 16+ | Chrome / Safari móvil con HTTPS habilitado |

---

## 🔌 API REST & Protocolo WebSocket

El servidor FastAPI expone tanto endpoints REST convencionales como el canal WebSocket dúplex para audio en tiempo real:

### Endpoints REST
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/health` | Chequeo de salud del servicio y disponibilidad de GPU NVIDIA. |
| `GET` | `/api/notes` | Lista todas las notas de voz guardadas en la base de datos SQLite. |
| `POST` | `/api/notes` | Crea manualmente una nueva nota de voz. |
| `DELETE` | `/api/notes/{id}` | Elimina una nota por su identificador. |
| `POST` | `/api/notes/synthesize` | Genera una síntesis ejecutiva de todas las notas usando LLaMA 3.2. |
| `GET` | `/api/telemetry/gpu` | Retorna telemetría en vivo: VRAM ocupada/libre, temperatura y nombre de GPU. |
| `GET` | `/api/user-profile` | Obtiene el perfil de usuario activo (nombre, nivel de inglés, intereses). |
| `PUT` | `/api/user-profile` | Actualiza campos del perfil de usuario persistente. |
| `DELETE` | `/api/history` | Vacía el historial de conversaciones, notas y vocabulario guardado. |

### Canal WebSocket (`/ws/chat`)
* **Cliente $\rightarrow$ Servidor:**
  * `audio_final`: Envía búfer WAV 16kHz PCM para transcripción completa de fin de turno.
  * `audio_stream`: Streaming progresivo de audio para transcripción parcial en tiempo real.
  * `interrupt`: Señal de cancelación inmediata (barge-in) para silenciar la generación.
  * `set_mode`: Cambia modo de conversación (`"es"`, `"en"`, `"auto"`).
  * `set_voice`: Selecciona voz individual o Voice Blend (`"blend_dora_sarah"`, etc.).
  * `set_personality`: Cambia persona activa (`"coach"`, `"friendly"`, `"tech"`, `"executive"`, `"interviewer"`).
  * `set_whisper_mode`: Activa/desactiva la modulación acústica de susurro (`true`/`false`).
* **Servidor $\rightarrow$ Cliente:**
  * `user_partial_transcription`: Texto parcial en vivo mientras el usuario habla.
  * `user_transcription`: Transcripción final fijada con latencia STT en milisegundos.
  * `ai_chunk`: Fragmentos de texto generados en streaming por LLaMA 3.2.
  * `audio_chunk`: Paquetes de audio sintetizados en base64 listos para reproducción gapless.
  * `tool_executed`: Notificación de herramienta ejecutada con datos y respuesta enriquecida.
  * `ai_done`: Cierre de turno con tiempo total de respuesta.

---

## 🧩 Ecosistema de Skills Modulares (Agensi.io / Claude Code / Cursor / Copilot)

La arquitectura del proyecto está desacoplada de tal manera que sus componentes clave pueden empaquetarse e instalarse como **Skills (`SKILL.md`)** en agentes de software como **Claude Code, Cursor, Windsurf, Copilot** o distribuirse en marketplaces como **[Agensi.io](https://agensi.io)**:

1. **Sub-Sentence Gapless Chunker:** Algoritmo de división progresiva de oraciones y cláusulas con retención de latencia sub-segundo.
2. **Zero-Latency Hybrid SQLite RAG:** Búsqueda vectorial semántica (3072D Cosine) y léxica (FTS5) en SQLite local.
3. **Web Audio VAD & Barge-In:** Controlador en cliente para corte inmediato de audio (<50 ms) y filtrado de ruido.

---

## ❓ Preguntas Frecuentes & Solución de Problemas (FAQ)

### 1. ¿Por qué el micrófono no se activa al abrir la web desde mi celular?
Los navegadores modernos (Chrome y Safari móvil) **bloquean el acceso al micrófono si la conexión no es HTTPS**. Nuestro servidor genera certificados SSL locales en `certs/`:
* Asegúrate de entrar con `https://<tu-ip-local>:8000`.
* En Chrome/Safari verás la advertencia de *"Certificado autofirmado / No seguro"*; pulsa en **"Configuración avanzada"** $\rightarrow$ **"Continuar a este sitio"**. El micrófono funcionará de inmediato.

### 2. Error en Windows: `Could not load library cublas64_12.dll`
Si Faster-Whisper no detecta CUDA en Windows, instala los paquetes oficiales de NVIDIA en tu entorno virtual:
```powershell
pip install nvidia-cublas-cu12 nvidia-cuda-nvrtc-cu12
```
El archivo `core/config.py` detectará automáticamente estas DLLs y las agregará al `PATH` en el arranque.

### 3. ¿Cómo configurar Docker para usar mi GPU NVIDIA?
En Windows, asegúrate de tener **Docker Desktop con WSL 2** activado. En Linux, instala el paquete `nvidia-container-toolkit`:
```bash
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
docker compose up --build
```

---

## 🏛️ Estructura del Proyecto

```text
├── core/
│   ├── __init__.py           # Exportación limpia y carga modular
│   ├── config.py             # Configuración centralizada, rutas, DLLs CUDA y personalidades
│   ├── chunker.py            # SentenceChunker: división gapless de oraciones fluidas
│   ├── stt.py                # Faster-Whisper CUDA fp16 con filtro de energía vocal
│   ├── tts.py                # Kokoro ONNX multihilo, Voice Blends y Modo Susurro
│   ├── llm.py                # Streaming Ollama Llama 3.2 y análisis pedagógico
│   └── utils.py              # Heurísticas de idioma y sanitización fonética
├── static/
│   ├── index.html            # Dashboard conversacional responsivo
│   ├── style.css             # UI futurista (Dark Glassmorphism, animaciones 60 FPS)
│   ├── app.js                # Orquestador del cliente (AudioContext, WebSocket, VAD)
│   ├── sw.js                 # Service Worker para capacidades offline y PWA
│   ├── manifest.json         # Manifiesto PWA para instalación móvil nativa
│   ├── locales.json          # Diccionarios de 8 idiomas internacionales
│   └── js/
│       ├── i18n.js           # Gestor multiidioma sincrónico con fallbacks
│       ├── earcons.js        # Sintetizador Web Audio API de chimes y feedback acústico
│       ├── audio-player.js   # Reproductor de audio con cola gapless y rate control
│       ├── audio-recorder.js # Grabación 16kHz PCM con VAD y RMS adaptativo
│       ├── chat-ui.js        # Renderizado de burbujas, orbe 60 FPS y badges de tools
│       ├── notes-drawer.js   # Drawer lateral de gestión y síntesis de notas
│       ├── telemetry.js      # Polling de telemetría de hardware y GPU NVIDIA
│       ├── visualizer.js     # Renderizador de osciloscopio en tiempo real
│       └── wav-encoder.js    # Codificador cliente PCM a WAV 16kHz
├── tests/
│   ├── run_all_tests.py      # Quality Gate principal (38 tests automatizados)
│   ├── benchmark_full_calibration_suite.py  # Benchmark E2E en vivo con telemetría WSS
│   ├── test_e2e_pipeline.py  # Pruebas integrales de ciclo de vida completo
│   ├── test_tools_memory.py  # Pruebas de herramientas y persistencia
│   ├── test_chunker.py       # Pruebas de segmentación de texto
│   └── test_sanitization.py  # Pruebas de filtros y limpieza de texto
├── database.py               # Capa SQLite (Hybrid RAG: Cosine 3072D + FTS5)
├── tools.py                  # Despachador de herramientas locales con latencia cero
├── server.py                 # Orquestador FastAPI WebSocket con soporte HTTPS
├── Dockerfile                # Imagen Docker optimizada para producción
├── docker-compose.yml        # Stack completo con Ollama GPU y Voice Assistant
├── requirements.txt          # Dependencias de Python fijadas
└── README.md                 # Documentación técnica completa
```

---

## 👤 Autor & Créditos

Desarrollado y mantenido con dedicación por **Cristian Arboleda** ([@cristianhar](https://github.com/cristianhar)).

* **GitHub:** [https://github.com/cristianhar](https://github.com/cristianhar)
* **Repositorio Oficial:** [https://github.com/cristianhar/realtime-voice-assistant-local](https://github.com/cristianhar/realtime-voice-assistant-local)
* **Licencia:** MIT License. Consulta el archivo [LICENSE](LICENSE) para más detalles.
* **Agradecimientos:** [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper), [Kokoro-ONNX](https://github.com/thewh1teagle/kokoro-onnx), [Ollama](https://ollama.com) y la comunidad open-source de Inteligencia Artificial Local.
