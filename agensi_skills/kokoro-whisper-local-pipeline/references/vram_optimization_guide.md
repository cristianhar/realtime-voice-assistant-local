# VRAM Optimization Guide for 6GB NVIDIA GPUs

When deploying local voice AI on consumer GPUs (e.g. RTX 4050 Laptop with 6GB VRAM), VRAM starvation leads to CUDA Out of Memory (OOM) errors or heavy swap thrashing. Follow this allocation profile:

### Recommended Allocation Profile
1. **Ollama LLM Engine**:
   - Model: `llama3.2:3b` (Quantized Q4_K_M).
   - VRAM usage: ~2.1 GB.
   - Ollama setting: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_FLASH_ATTENTION=1`.

2. **Faster-Whisper STT**:
   - Model: `base` (or `small`).
   - Device: `cuda`, compute_type: `float16`.
   - VRAM usage: ~420 MB.
   - Beam size: `1` (Greedy decoding is 3x faster with negligible accuracy difference for conversational speech).

3. **Kokoro TTS Engine**:
   - Execution Provider: `CPUExecutionProvider` with ONNX Runtime.
   - VRAM usage: **0 MB** (Runs entirely in host system RAM with 4 parallel threads).
   - Latency: ~400ms per synthesized clause, completely avoiding GPU memory competition.

