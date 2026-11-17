---
name: realtime-voice-barge-in
description: Implement full-duplex conversational voice loops with sub-50ms instant barge-in interruption, Web Audio VAD, and gapless streaming audio playback for AI agents.
---

# Realtime Voice Barge-In & Full-Duplex Audio Loop

## Overview
This skill equips AI coding agents (Claude Code, Cursor, Copilot, Antigravity) with production-ready patterns, client scripts, and backend protocols to implement real-time conversational voice loops with **sub-50ms instant barge-in interruption**.

Barge-in allows users to interrupt an AI assistant mid-speech naturally—just like a real phone call or human conversation—instantly canceling playback, clearing buffers, and switching the system to active listening mode without audio artifacts.

---

## When to Use This Skill
Activate this skill when:
- Building web, mobile, or desktop voice agents (similar to ChatGPT Voice Mode, ElevenLabs Conversational AI, Hume, or Vapi).
- Needing ultra-low latency (<50ms) user interruption and echo cancellation.
- Implementing Web Audio API Voice Activity Detection (VAD) with progressive RMS energy filtering.
- Streaming PCM audio chunks over WebSockets with gapless sequential playback queues.

---

## Core Architecture & Workflow

### 1. Full-Duplex Audio Pipeline
```
[User Mic] -> [Web Audio VAD] -> [16kHz PCM Chunks] -> [WebSocket /ws/chat]
                                                             |
                                                       [Backend Loop]
                                                             |
[Web Audio Queue] <- [Gapless Playback] <- [WAV/PCM] <-------+
```

### 2. Sub-50ms Barge-In Trigger Protocol
When the client-side VAD detects incoming user speech while AI audio is actively playing:
1. **Client immediately stops local audio output**:
   - Clears the Web Audio source node (`source.stop(0)`).
   - Flushes the queued audio chunk array.
   - Resets playback state to `idle`.
2. **Client emits barge-in control packet**:
   ```json
   {
     "type": "interrupt"
   }
   ```
3. **Backend cancels pending inference**:
   - Cancels the active LLM streaming generator.
   - Clears queued TTS synthesis tasks.
   - Sends confirmation acknowledgment:
   ```json
   {
     "type": "interrupted",
     "timestamp": 1700000000.123
   }
   ```

---

## Bundled Tools & Assets
- `scripts/vad_audio_processor.js`: High-performance Web Audio AudioWorklet / ScriptProcessor for 16kHz PCM downsampling and RMS energy measurement.
- `scripts/barge_in_harness.py`: Standalone Python WebSocket test server to benchmark interrupt response latency.
- `templates/voice_client_snippet.html`: Drop-in, responsive HTML/JS full-duplex client with synthetic earcons and visual volume ring.
- `references/latency_budget.md`: Millisecond-by-millisecond breakdown of acoustic, network, and processing latency.

---

## Implementation Guidelines for Agents
1. **Always use 16kHz Mono PCM**: Whisper and local STT models expect single-channel 16,000 Hz audio. Downsampling in the browser prevents unnecessary network transfer and server-side resamplers.
2. **Sequential Audio Buffer Queue**: Never play streaming audio chunks simultaneously. Maintain a strictly ordered queue where chunk `N+1` plays precisely at `N.startTime + N.duration`.
3. **Double-Barrier Interruption**: Cut audio client-side first (<10ms perceived latency), then inform the server. Never wait for a server round-trip before silencing local speakers.
4. **Non-Blocking WebSocket Receiver**: Never await LLM streams or TTS synthesis inside the main `while True: await websocket.receive_json()` loop. Delegate turn execution to an independent `asyncio.Task` so the socket can receive `{"type": "interrupt"}` frames at any millisecond without TCP buffering delay.
5. **Context Truncation (`conversation.item.truncate`)**: When interrupted, truncate the assistant's utterance in conversation history and persistent database to only the sentences physically spoken before the cut (`"..." [interrumpido]`), allowing the next LLM turn to naturally adapt to the interruption.

