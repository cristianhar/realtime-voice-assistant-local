// ==============================================================================
// Voice Assistant - Audio Player Manager (Gapless Queue & Interruption Control)
// ==============================================================================

class AudioPlayerManager {
    constructor(options = {}) {
        this.audioQueue = [];
        this.currentAudioElement = null;
        this.isAudioPlaying = false;
        this.playbackSpeed = options.playbackSpeed || 1.0;

        this.onPlayStart = options.onPlayStart || (() => {});
        this.onPlayEnd = options.onPlayEnd || (() => {});
        this.onInterrupt = options.onInterrupt || (() => {});

        // Sincronización robusta por turno conversacional
        this.activeTurnId = null;
        this.isTurnComplete = false;
        this.graceTimeout = null;
    }

    setPlaybackSpeed(speed) {
        const val = parseFloat(speed);
        if (!isNaN(val) && val >= 0.5 && val <= 2.5) {
            this.playbackSpeed = val;
            if (this.currentAudioElement) {
                this.currentAudioElement.playbackRate = val;
            }
        }
    }

    startTurn(turnId) {
        if (this.graceTimeout) {
            clearTimeout(this.graceTimeout);
            this.graceTimeout = null;
        }
        this.activeTurnId = turnId || ("turn-" + Date.now());
        this.isTurnComplete = false;
    }

    markTurnComplete(turnId) {
        if (!turnId || turnId === this.activeTurnId) {
            this.isTurnComplete = true;
            if (this.audioQueue.length === 0 && !this.isPlayingAudioNow()) {
                this.finalizeTurn();
            }
        }
    }

    isPlayingAudioNow() {
        return !!(this.currentAudioElement && !this.currentAudioElement.paused && !this.currentAudioElement.ended);
    }

    enqueueAudio(base64Wav, turnId = null) {
        if (!base64Wav) return;
        if (this.graceTimeout) {
            clearTimeout(this.graceTimeout);
            this.graceTimeout = null;
        }
        if (turnId && !this.activeTurnId) {
            this.activeTurnId = turnId;
        }

        const audioObj = new Audio("data:audio/wav;base64," + base64Wav);
        audioObj.preload = "auto";
        this.audioQueue.push(audioObj);

        // Si NO hay ningún elemento de audio reproduciéndose activamente en este instante físico,
        // reproducir el siguiente de la cola de inmediato (elimina el bloqueo por cola vacía previa).
        if (!this.isPlayingAudioNow()) {
            this.playNextChunk();
        }
    }

    playNextChunk() {
        if (this.graceTimeout) {
            clearTimeout(this.graceTimeout);
            this.graceTimeout = null;
        }

        // Si la cola está vacía
        if (this.audioQueue.length === 0) {
            this.currentAudioElement = null;

            // Si el turno aún está generando audio en streaming, esperar breve ventana de gracia
            if (!this.isTurnComplete && this.activeTurnId) {
                this.graceTimeout = setTimeout(() => {
                    this.graceTimeout = null;
                    if (this.audioQueue.length === 0 && !this.isPlayingAudioNow()) {
                        this.finalizeTurn();
                    }
                }, 500);
                return;
            }

            this.finalizeTurn();
            return;
        }

        // Respiración sutil solo al inicio absoluto del turno, nunca entre oraciones consecutivas
        if (!this.isAudioPlaying && window.voiceHumanizer) {
            window.voiceHumanizer.playPreSpeechBreath();
        }

        this.isAudioPlaying = true;
        window.isAudioPlaying = true;
        this.onPlayStart();

        const audioObj = this.audioQueue.shift();
        this.currentAudioElement = audioObj;
        this.currentAudioElement.playbackRate = this.playbackSpeed;

        this.currentAudioElement.onended = () => {
            this.currentAudioElement = null;
            this.playNextChunk();
        };

        this.currentAudioElement.onerror = (e) => {
            console.error("[AudioPlayer] Error en reproducción de audio chunk:", e);
            this.currentAudioElement = null;
            this.playNextChunk();
        };

        this.currentAudioElement.play().catch(e => {
            console.warn("[AudioPlayer] Autoplay bloqueado o abortado:", e);
            this.currentAudioElement = null;
            this.playNextChunk();
        });
    }

    finalizeTurn() {
        if (this.graceTimeout) {
            clearTimeout(this.graceTimeout);
            this.graceTimeout = null;
        }
        this.isAudioPlaying = false;
        this.currentAudioElement = null;
        this.activeTurnId = null;
        this.isTurnComplete = false;
        window.isAudioPlaying = false;
        if (window.voiceHumanizer) window.voiceHumanizer.resetTurn();
        this.onPlayEnd();
    }

    interrupt() {
        if (this.graceTimeout) {
            clearTimeout(this.graceTimeout);
            this.graceTimeout = null;
        }
        if (this.currentAudioElement) {
            this.currentAudioElement.pause();
            this.currentAudioElement = null;
        }
        this.audioQueue.length = 0;
        this.isAudioPlaying = false;
        this.activeTurnId = null;
        this.isTurnComplete = false;
        window.isAudioPlaying = false;
        if (window.voiceHumanizer) window.voiceHumanizer.resetTurn();
        this.onInterrupt();
    }
}

window.AudioPlayerManager = AudioPlayerManager;
