#!/usr/bin/env bash
# ==============================================================================
# Realtime Voice Assistant Local - 1-Line Universal Linux/macOS Installer
# Run: curl -fsSL https://raw.githubusercontent.com/cristianhar/realtime-voice-assistant-local/main/install.sh | bash
# ==============================================================================
set -e

echo -e "\033[1;36m==================================================================\033[0m"
echo -e "\033[1;36m  🎙️ INSTALADOR AUTOMÁTICO: REALTIME VOICE ASSISTANT LOCAL\033[0m"
echo -e "\033[1;37m  100% Offline | Sub-50ms Interruption | Calibrado para 6GB VRAM\033[0m"
echo -e "\033[1;36m==================================================================\033[0m"

# 1. Verificar Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "\033[1;31m[ERROR] Python 3 no está instalado. Instálalo con tu gestor de paquetes (apt, brew, dnf).\033[0m"
    exit 1
fi

# 2. Directorio de instalación
if [ ! -f "server.py" ]; then
    INSTALL_DIR="$HOME/VoiceAssistantLocal"
    if [ ! -d "$INSTALL_DIR" ]; then
        echo -e "\033[1;33m[1/5] Clonando repositorio en $INSTALL_DIR...\033[0m"
        git clone https://github.com/cristianhar/realtime-voice-assistant-local.git "$INSTALL_DIR"
    fi
    cd "$INSTALL_DIR"
fi

# 3. Virtual Environment
echo -e "\033[1;33m[2/5] Creando entorno virtual venv...\033[0m"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 4. Dependencias
echo -e "\033[1;33m[3/5] Instalando dependencias de Python...\033[0m"
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet -r requirements.txt

# 5. Modelos
echo -e "\033[1;33m[4/5] Verificando modelos neuronales locales...\033[0m"
if [ -f "setup_models.py" ]; then
    ./venv/bin/python setup_models.py
fi

echo -e "\033[1;32m==================================================================\033[0m"
echo -e "\033[1;32m  ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE\033[0m"
echo -e "\033[1;37m  Iniciando servidor local en https://localhost:8000 ...\033[0m"
echo -e "\033[1;32m==================================================================\033[0m"

chmod +x launch_voice_assistant.sh
./launch_voice_assistant.sh
