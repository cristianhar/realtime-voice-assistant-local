// vad_audio_processor.js - Production Web Audio VAD & 16kHz Downsampler
class RealtimeAudioProcessor {
  constructor(options = {}) {
    this.sampleRate = options.sampleRate || 16000;
    this.vadThreshold = options.vadThreshold || 0.015;
    this.silenceDurationMs = options.silenceDurationMs || 700;
    this.audioContext = null;
    this.mediaStream = null;
    this.processor = null;
    this.isSpeaking = false;
    this.silenceStart = null;
    this.onSpeechStart = options.onSpeechStart || (() => {});
    this.onSpeechEnd = options.onSpeechEnd || (() => {});
    this.onAudioChunk = options.onAudioChunk || (() => {});
  }

  async start() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000
    });
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });

    const source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      let sumSquares = 0.0;
      for (let i = 0; i < inputData.length; i++) {
        sumSquares += inputData[i] * inputData[i];
      }
      const rms = Math.sqrt(sumSquares / inputData.length);

      if (rms > this.vadThreshold) {
        if (!this.isSpeaking) {
          this.isSpeaking = true;
          this.onSpeechStart(rms);
        }
        this.silenceStart = null;
      } else {
        if (this.isSpeaking) {
          if (!this.silenceStart) {
            this.silenceStart = performance.now();
          } else if (performance.now() - this.silenceStart > this.silenceDurationMs) {
            this.isSpeaking = false;
            this.onSpeechEnd();
            this.silenceStart = null;
          }
        }
      }

      // Convert float32 to 16-bit signed PCM
      const pcm16 = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.onAudioChunk(pcm16.buffer, rms, this.isSpeaking);
    };

    source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
  }

  stop() {
    if (this.processor) this.processor.disconnect();
    if (this.mediaStream) this.mediaStream.getTracks().forEach(t => t.stop());
    if (this.audioContext) this.audioContext.close();
  }
}

if (typeof module !== 'undefined') module.exports = { RealtimeAudioProcessor };

