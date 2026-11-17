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
    timeout /t 4 >nul
)

echo [✓] Iniciando servidor HTTPS en https://localhost:8000 (Multi-dispositivo)...
echo [✓] Abriendo navegador en: https://localhost:8000
start https://localhost:8000

.\venv\Scripts\python.exe server.py --https --host 0.0.0.0 --port 8000
pause

