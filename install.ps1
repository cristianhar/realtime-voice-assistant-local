# ==============================================================================
# Realtime Voice Assistant Local - 1-Line Universal Windows Installer
# Run: irm https://raw.githubusercontent.com/cristianhar/realtime-voice-assistant-local/main/install.ps1 | iex
# ==============================================================================
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  🎙️ INSTALADOR AUTOMÁTICO: REALTIME VOICE ASSISTANT LOCAL" -ForegroundColor Cyan
Write-Host "  100% Offline | Sub-50ms Interruption | Calibrado para 6GB VRAM" -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Verificar Python 3.10+
Write-Host "[1/6] Verificando entorno Python..." -ForegroundColor Yellow
$pythonExe = ""
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonExe = "py"
} else {
    Write-Host "[ERROR] No se encontró Python en el sistema." -ForegroundColor Red
    Write-Host "Por favor instala Python 3.10 o superior desde https://www.python.org/downloads/ y marca 'Add Python to PATH'." -ForegroundColor Yellow
    Exit 1
}

# 2. Determinar directorio de instalación
$installDir = Get-Location
if (-not (Test-Path "server.py")) {
    $installDir = Join-Path $env:USERPROFILE "VoiceAssistantLocal"
    if (-not (Test-Path $installDir)) {
        Write-Host "[2/6] Clonando repositorio en $installDir..." -ForegroundColor Yellow
        git clone https://github.com/cristianhar/realtime-voice-assistant-local.git $installDir
    }
    Set-Location $installDir
} else {
    Write-Host "[2/6] Instalando directamente en el repositorio local..." -ForegroundColor Green
}

# 3. Crear entorno virtual
Write-Host "[3/6] Configurando entorno virtual venv..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    & $pythonExe -m venv venv
}

# 4. Instalar dependencias
Write-Host "[4/6] Instalando dependencias de Python (FastAPI, Whisper, Kokoro)..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.\venv\Scripts\python.exe -m pip install --quiet -r requirements.txt

# 5. Descargar modelos offline optimizados
Write-Host "[5/6] Verificando modelos neuronales locales (Whisper + Kokoro)..." -ForegroundColor Yellow
if (Test-Path "setup_models.py") {
    .\venv\Scripts\python.exe setup_models.py
}

# 6. Crear acceso directo de escritorio
Write-Host "[6/6] Creando acceso directo en tu Escritorio de Windows..." -ForegroundColor Yellow
if (Test-Path "create_desktop_shortcut.ps1") {
    powershell -ExecutionPolicy Bypass -File .\create_desktop_shortcut.ps1
}

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE (10/10)" -ForegroundColor Green
Write-Host "  Puedes abrir el asistente en cualquier momento desde el" -ForegroundColor White
Write-Host "  icono 'VoiceChat AI Local' en tu Escritorio." -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Green

# Iniciar automáticamente
Write-Host "Iniciando Asistente de Voz..." -ForegroundColor Cyan
Start-Process "launch_voice_assistant.bat"
