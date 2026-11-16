@echo off
title English Voice Practice AI - 100%% Local
cd /d "%~dp0"

echo ======================================================================
echo    INICIANDO ASISTENTE DE VOZ LOCAL PARA PRACTICAR INGLES
echo    Hardware: RTX CUDA (Faster-Whisper) + Kokoro TTS + Ollama
echo ======================================================================

REM Verificar si Ollama esta corriendo
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Iniciando servicio Ollama en segundo plano...
    start "" /B ollama serve
    timeout /t 3 >nul
)

echo [✓] Iniciando servidor FastAPI en http://127.0.0.1:8000 ...
echo [✓] Abre tu navegador en: http://127.0.0.1:8000
start http://127.0.0.1:8000

.\venv\Scripts\python.exe server.py
pause

