#!/usr/bin/env bash
# ==============================================================================
# VoiceChat AI Local - Linux / macOS 1-Click Terminal Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "====================================================================="
echo "  🎙️ VOICECHAT AI LOCAL - LINUX/MAC 1-CLICK LAUNCHER"
echo "====================================================================="

# 1. Check Virtual Environment
if [ ! -f "venv/bin/python" ]; then
    echo "[!] Virtual environment not found in 'venv'. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 2. Check Kokoro TTS Models
mkdir -p models
if [ ! -f "models/kokoro-v0_19.onnx" ]; then
    echo "[!] Downloading Kokoro-82M ONNX model (~310 MB)..."
    curl -L "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v0_19.onnx" -o "models/kokoro-v0_19.onnx"
fi
if [ ! -f "models/voices-v1.0.bin" ]; then
    echo "[!] Downloading Kokoro voices (~28 MB)..."
    curl -L "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" -o "models/voices-v1.0.bin"
fi

# 3. Check Ollama Service
if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[*] Starting local Ollama daemon..."
    ollama serve >/dev/null 2>&1 &
    sleep 3
fi

# 4. Open Browser
(sleep 2 && (xdg-open "https://localhost:8000" 2>/dev/null || open "https://localhost:8000" 2>/dev/null || true)) &

# 5. Start Voice Server
echo "[*] Starting FastAPI HTTPS server..."
python server.py --https --host 0.0.0.0 --port 8000

