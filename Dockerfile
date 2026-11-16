# Realtime Local Voice Assistant - Dockerfile
# Optimized for Python 3.10, FastAPI, Faster-Whisper, Kokoro TTS & Ollama

FROM python:3.10-slim

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (audio processing & networking)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose default HTTP/HTTPS port
EXPOSE 8000

# Start Realtime Voice Assistant with HTTPS enabled for mobile microphone support
CMD ["python", "server.py", "--https", "--host", "0.0.0.0", "--port", "8000"]
