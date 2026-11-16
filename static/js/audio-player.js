// ==============================================================================
// Voice Assistant - Audio Player Manager (Gapless Queue & Interruption Control)
// ==============================================================================

class AudioPlayerManager {
    constructor(options = {}) {
        this.audioQueue = [];
        this.currentAudioElement = null;
        this.isAudioPlaying = false;

        this.onPlayStart = options.onPlayStart || (() => {});
        this.onPlayEnd = options.onPlayEnd || (() => {});
        this.onInterrupt = options.onInterrupt || (() => {});
    }

    enqueueAudio(base64Wav) {
        if (!base64Wav) return;
        const audioObj = new Audio("data:audio/wav;base64," + base64Wav);
        audioObj.preload = "auto";
        this.audioQueue.push(audioObj);

        if (!this.isAudioPlaying) {
            this.playNextChunk();
        }
    }

    playNextChunk() {
        if (this.audioQueue.length === 0) {
            this.isAudioPlaying = false;
            this.currentAudioElement = null;
            window.isAudioPlaying = false;
            this.onPlayEnd();
            return;
        }

        this.isAudioPlaying = true;
        window.isAudioPlaying = true;
        this.onPlayStart();

        this.currentAudioElement = this.audioQueue.shift();

        this.currentAudioElement.onended = () => {
            this.playNextChunk();
        };

        this.currentAudioElement.onerror = (e) => {
            console.error("[AudioPlayer] Error en reproducción:", e);
            this.playNextChunk();
        };

        this.currentAudioElement.play().catch(e => {
            console.warn("[AudioPlayer] Autoplay bloqueado:", e);
            this.playNextChunk();
        });
    }

    interrupt() {
        if (this.currentAudioElement) {
            this.currentAudioElement.pause();
            this.currentAudioElement = null;
        }
        this.audioQueue.length = 0;
        this.isAudioPlaying = false;
        window.isAudioPlaying = false;
        this.onInterrupt();
    }
}

window.AudioPlayerManager = AudioPlayerManager;

