---
name: kokoro-whisper-local-pipeline
description: High-performance, 100% offline STT & TTS pipeline calibrated for 6GB VRAM GPUs using Faster-Whisper CUDA and multithreaded Kokoro ONNX with voice blending.
---

# Kokoro & Whisper Local Voice Pipeline

## Overview
This skill guides AI agents in setting up, optimizing, and operating a **100% offline, privacy-first speech-to-text (STT) and text-to-speech (TTS) pipeline** calibrated to run concurrently with local LLMs on entry-level NVIDIA GPUs with **6GB VRAM** (such as RTX 3060, RTX 4050, or RTX 4060 Laptop).

It eliminates cloud API latency and recurring costs by orchestrating **Faster-Whisper (CUDA float16)** for sub-30ms voice transcription alongside **Kokoro-82M (multithreaded ONNX)** for ultra-realistic speech synthesis with custom voice blending.

---

## When to Use This Skill
Activate this skill when:
- Deploying offline voice assistants on local hardware with limited GPU VRAM (4GB - 8GB).
- Requiring real-time conversational STT (~25ms inference latency per chunk).
- Requiring ultra-natural, expressive TTS (~400ms first-chunk response) without paying ElevenLabs or OpenAI TTS fees.
- Needing voice sanitization to prevent TTS hallucination over markdown formatting, bullet points, asterisks, URLs, and code blocks.
- Implementing interpolated voice blending (e.g., 60% Voice A + 40% Voice B).

---

## Memory & VRAM Footprint Calibration (6 GB VRAM Target)

```
[Total Available GPU VRAM: 6,144 MB]
  |-- Llama-3.2-3B-Instruct (4-bit Q4_K_M via Ollama): ~2,100 MB
  |-- Faster-Whisper Base (float16 CUDA Kernels):         ~420 MB
  |-- Kokoro-82M (multithreaded CPU Execution Provider):     0 MB (Runs on RAM / CPU threads)
  |-- PyTorch CUDA Context & OS Desktop Display:       ~1,400 MB
  +-------------------------------------------------------------
  Remaining Free VRAM Headroom:                        ~2,224 MB
```

---

## Bundled Tools & Assets
- `scripts/stt_whisper_engine.py`: Faster-Whisper runner with CUDA auto-detection, warm-up inference, and CPU int8 fallback.
- `scripts/tts_kokoro_sanitizer.py`: Advanced regex text sanitizer and voice vector interpolation engine.
- `references/vram_optimization_guide.md`: Detailed hardware tuning, CUDA thread allocation, and ONNX graph optimization.
- `references/phoneme_voice_blends.md`: Catalog of voice personalities and linear blend ratios.
- `templates/docker-compose.voice.yml`: Complete container deployment with NVIDIA GPU pass-through.

---

## Production Rules for Agents
1. **Never pass raw markdown to TTS**: Strip asterisks (`*`), hashtags (`#`), backticks (```), brackets, and URLs before calling the phonemizer to prevent the synthesizer from reading symbols aloud.
2. **Warm-up CUDA Kernels on Startup**: Execute a dummy 1-second silence inference through Whisper upon loading to compile GPU kernels ahead of the first user interaction.
3. **Run Kokoro on Multithreaded CPU**: Offloading Kokoro's ONNX session to CPU with 4 dedicated threads frees up over 500 MB of VRAM for the STT and LLM, allowing smooth concurrent processing.
