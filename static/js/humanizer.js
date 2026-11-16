// ==============================================================================
// Voice Assistant - Voice Humanizer (Micro-inhalations & Conversational Timing)
// ==============================================================================

class VoiceHumanizer {
    constructor(options = {}) {
        this.enabled = options.enabled !== undefined ? options.enabled : true;
        this.breathVolume = options.breathVolume || 0.12; // -18 dB subtle intake
        this.audioCtx = null;
        this.breathAudio = null;
        this.hasPlayedInTurn = false;
        this.init();
    }

    init() {
        try {
            this.breathAudio = new Audio("/static/audio/breath_subtle.wav");
            this.breathAudio.preload = "auto";
            this.breathAudio.volume = this.breathVolume;
        } catch (e) {
            console.warn("[Humanizer] No se pudo precargar audio de respiración estático:", e);
        }
    }

    getAudioContext() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioCtx = new AudioContext();
        }
        if (this.audioCtx.state === "suspended") {
            this.audioCtx.resume();
        }
        return this.audioCtx;
    }

    playPreSpeechBreath() {
        if (!this.enabled || this.hasPlayedInTurn) return;
        this.hasPlayedInTurn = true;

        // Intentar reproducir el sample de audio grabado/sintetizado
        if (this.breathAudio) {
            this.breathAudio.currentTime = 0;
            this.breathAudio.volume = this.breathVolume;
            const playPromise = this.breathAudio.play();
            if (playPromise !== undefined) {
                playPromise.catch(() => {
                    // Fallback procedural en caso de política de autoplay o ruta
                    this.synthesizeProceduralBreath();
                });
            }
        } else {
            this.synthesizeProceduralBreath();
        }
    }

    // Fallback acústico 100% autónomo con Web Audio API (ruido rosa con filtro resonante vocal)
    synthesizeProceduralBreath() {
        try {
            const ctx = this.getAudioContext();
            const sampleRate = ctx.sampleRate;
            const duration = 0.085; // 85 ms
            const bufferSize = Math.floor(sampleRate * duration);
            const buffer = ctx.createBuffer(1, bufferSize, sampleRate);
            const output = buffer.getChannelData(0);

            // Generador de ruido filtrado con envolvente de inhalación
            let b0 = 0, b1 = 0, b2 = 0;
            for (let i = 0; i < bufferSize; i++) {
                const t = i / bufferSize;
                // Envolvente de inhalación: subida suave, pico al 75%, caída asintótica
                const env = t < 0.75 
                    ? Math.sin((t / 0.75) * (Math.PI / 2)) * 1.5
                    : Math.cos(((t - 0.75) / 0.25) * (Math.PI / 2));
                const white = Math.random() * 2 - 1;
                b0 = 0.99 * b0 + white * 0.05;
                b1 = 0.95 * b1 + white * 0.15;
                b2 = 0.85 * b2 + white * 0.30;
                output[i] = (b0 + b1 + b2) * env * 0.08;
            }

            const noiseNode = ctx.createBufferSource();
            noiseNode.buffer = buffer;

            // Filtro resonante paso banda simula la cavidad de la garganta (1,600 Hz)
            const filter = ctx.createBiquadFilter();
            filter.type = "bandpass";
            filter.frequency.setValueAtTime(1600, ctx.currentTime);
            filter.Q.setValueAtTime(1.8, ctx.currentTime);

            const gainNode = ctx.createGain();
            gainNode.gain.setValueAtTime(this.breathVolume, ctx.currentTime);

            noiseNode.connect(filter);
            filter.connect(gainNode);
            gainNode.connect(ctx.destination);

            noiseNode.start();
        } catch (e) {
            console.error("[Humanizer] Fallback procedural error:", e);
        }
    }

    resetTurn() {
        this.hasPlayedInTurn = false;
        if (this.breathAudio) {
            try {
                this.breathAudio.pause();
                this.breathAudio.currentTime = 0;
            } catch (e) {}
        }
    }
}

// Instancia global
window.voiceHumanizer = new VoiceHumanizer();
