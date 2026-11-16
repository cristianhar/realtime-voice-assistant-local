@echo off
setlocal enabledelayedexpansion
title VoiceChat AI Local - Initializing...
color 0B

echo =====================================================================
echo   🎙️ VOICECHAT AI LOCAL - INICIADOR DE ESCRITORIO DE 1-CLIC
echo   100%% Local, Privado, Tiempo Real y Baja Latencia
echo =====================================================================
echo.

cd /d "%~dp0"

:: 1. Verificar Entorno Virtual Python
if not exist "venv\Scripts\python.exe" (
    echo [!] No se encontro el entorno virtual en 'venv'. Creando entorno...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el venv. Asegurate de tener Python 3.10+ instalado.
        pause
        exit /b 1
    )
    echo [*] Instalando dependencias requeridas...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    pip install nvidia-cublas-cu12 nvidia-cuda-nvrtc-cu12
)

:: 2. Verificar Modelos de Kokoro TTS
if not exist "models\kokoro-v0_19.onnx" (
    echo [!] Descargando modelo de voz Kokoro-82M ONNX (~310 MB)...
    if not exist "models" mkdir models
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v0_19.onnx' -OutFile 'models/kokoro-v0_19.onnx'"
)
if not exist "models\voices-v1.0.bin" (
    echo [!] Descargando voces Kokoro (~28 MB)...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin' -OutFile 'models/voices-v1.0.bin'"
)

:: 3. Verificar Servicio de Ollama
echo [*] Verificando servicio de Ollama...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [*] Ollama no esta activo. Iniciando daemon local de Ollama...
    start /b "" ollama serve >nul 2>&1
    timeout /t 3 /nobreak >nul
)

:: 4. Lanzar Navegador en Modo App Nativa (Ventana independiente sin barras)
echo [*] Abriendo interfaz conversacional en modo App Nativa...
set "BROWSER_LAUNCHED=0"
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    start "" cmd /c "timeout /t 2 /nobreak >nul & start """" ""%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"" --app=https://localhost:8000"
    set "BROWSER_LAUNCHED=1"
) else if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    start "" cmd /c "timeout /t 2 /nobreak >nul & start """" ""%ProgramFiles%\Google\Chrome\Application\chrome.exe"" --app=https://localhost:8000"
    set "BROWSER_LAUNCHED=1"
)
if "!BROWSER_LAUNCHED!"=="0" (
    start "" cmd /c "timeout /t 2 /nobreak >nul & start https://localhost:8000"
)

:: 5. Iniciar Servidor Principal FastAPI HTTPS
echo [*] Iniciando servidor FastAPI con aceleracion GPU...
echo [*] Conectate en tu PC:     https://localhost:8000
echo [*] Conectate en tu Celular: https://192.168.x.x:8000 (Misma red Wi-Fi)
echo =====================================================================
echo.

call venv\Scripts\activate.bat
python server.py --https --host 0.0.0.0 --port 8000

pause

