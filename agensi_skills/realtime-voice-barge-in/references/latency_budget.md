# Latency Budget: Sub-50ms Full-Duplex Voice Loop

To achieve conversational quality indistinguishable from ChatGPT Voice Mode, every millisecond of the audio loop is strictly accounted for:

| Stage | Operation | Typical Latency | SLA Threshold |
|---|---|:---:|:---:|
| **1. Client Capture** | Web Audio Worklet 16kHz buffer chunking | 12 - 16 ms | < 20 ms |
| **2. Client VAD** | Root Mean Square (RMS) threshold check | 0.2 - 0.5 ms | < 1 ms |
| **3. Client Mute** | `AudioBufferSourceNode.stop(0)` & queue wipe | 0.8 - 2.0 ms | < 5 ms |
| **4. Network (WS)** | WebSocket control frame transmission (`interrupt`) | 1 - 15 ms | < 25 ms |
| **5. Server Abort** | Asyncio task cancellation of LLM/TTS workers | 0.5 - 1.5 ms | < 5 ms |
| **Total Interruption Latency** | **Total end-to-end time to silence** | **~18 - 35 ms** | **< 50 ms** |

---

## Echo Cancellation Best Practices
1. Request browser echo cancellation explicitly:
   ```javascript
   navigator.mediaDevices.getUserMedia({
     audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
   });
   ```
2. When the user interrupts, ignore incoming audio frames for the first ~60ms to prevent the agent's own residual speaker output from being recognized as user speech.
