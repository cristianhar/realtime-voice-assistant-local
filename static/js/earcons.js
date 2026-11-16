// ==============================================================================
// Voice Assistant - Earcon Audio Feedback (Web Audio API Synthesizer)
// ==============================================================================

class EarconManager {
    constructor() {
        this.audioCtx = null;
        this.isEnabled = true;
    }

    _ensureContext() {
        if (!this.audioCtx) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.audioCtx.state === "suspended") {
            this.audioCtx.resume();
        }
    }

    playCallStart() {
        if (!this.isEnabled) return;
        this._ensureContext();
        // Arpegio ascendente suave: Do5 (523Hz) -> Mi5 (659Hz) -> Sol5 (784Hz)
        const notes = [523.25, 659.25, 783.99];
        const now = this.audioCtx.currentTime;
        notes.forEach((freq, idx) => {
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + idx * 0.08);

            gain.gain.setValueAtTime(0, now + idx * 0.08);
            gain.gain.linearRampToValueAtTime(0.12, now + idx * 0.08 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.08 + 0.28);

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);
            osc.start(now + idx * 0.08);
            osc.stop(now + idx * 0.08 + 0.3);
        });
    }

    playCallEnd() {
        if (!this.isEnabled) return;
        this._ensureContext();
        // Arpegio descendente: Sol5 (784Hz) -> Mi5 (659Hz) -> Do5 (523Hz)
        const notes = [783.99, 659.25, 523.25];
        const now = this.audioCtx.currentTime;
        notes.forEach((freq, idx) => {
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + idx * 0.07);

            gain.gain.setValueAtTime(0, now + idx * 0.07);
            gain.gain.linearRampToValueAtTime(0.10, now + idx * 0.07 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.07 + 0.25);

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);
            osc.start(now + idx * 0.07);
            osc.stop(now + idx * 0.07 + 0.26);
        });
    }

    playBargeIn() {
        if (!this.isEnabled) return;
        this._ensureContext();
        // Clic sutil de baja frecuencia: 280Hz -> 140Hz
        const now = this.audioCtx.currentTime;
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(280, now);
        osc.frequency.exponentialRampToValueAtTime(140, now + 0.05);

        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);
        osc.start(now);
        osc.stop(now + 0.06);
    }

    playToolSuccess() {
        if (!this.isEnabled) return;
        this._ensureContext();
        // Doble ping armónico: La5 (880Hz) -> Do6 (1046Hz)
        const notes = [880.00, 1046.50];
        const now = this.audioCtx.currentTime;
        notes.forEach((freq, idx) => {
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, now + idx * 0.06);

            gain.gain.setValueAtTime(0, now + idx * 0.06);
            gain.gain.linearRampToValueAtTime(0.09, now + idx * 0.06 + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.06 + 0.20);

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);
            osc.start(now + idx * 0.06);
            osc.stop(now + idx * 0.06 + 0.22);
        });
    }
}

window.EarconManager = EarconManager;
