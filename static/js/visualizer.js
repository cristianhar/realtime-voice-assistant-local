// static/js/visualizer.js - Visualizador de Audio 60 FPS en Canvas
const AudioVisualizer = {
    canvas: null,
    ctx: null,
    animationId: null,
    analyser: null,

    init(canvasId = "audio-visualizer-canvas") {
        this.canvas = document.getElementById(canvasId);
        if (this.canvas) {
            this.ctx = this.canvas.getContext("2d");
            this.start();
        }
    },

    setAnalyser(analyserNode) {
        this.analyser = analyserNode;
    },

    start() {
        if (!this.animationId && this.ctx) {
            this.loop = this.loop.bind(this);
            this.loop();
        }
    },

    loop() {
        this.animationId = requestAnimationFrame(this.loop);
        if (!this.canvas || !this.ctx) return;

        const width = this.canvas.width;
        const height = this.canvas.height;
        this.ctx.clearRect(0, 0, width, height);
        const centerY = height / 2;

        if (window.isAudioPlaying) {
            // IA Hablando: Onda armónica lumínica violeta y cian
            const time = Date.now() * 0.005;
            this.ctx.lineWidth = 2.5;
            this.ctx.strokeStyle = "#a855f7";
            this.ctx.shadowBlur = 12;
            this.ctx.shadowColor = "#c084fc";

            this.ctx.beginPath();
            for (let x = 0; x < width; x++) {
                const progress = x / width;
                const envelope = Math.sin(progress * Math.PI);
                const y = centerY + Math.sin(x * 0.04 + time * 3) * 16 * envelope
                                  + Math.sin(x * 0.08 - time * 2) * 8 * envelope;
                if (x === 0) this.ctx.moveTo(x, y);
                else this.ctx.lineTo(x, y);
            }
            this.ctx.stroke();

            // Armónica Cian
            this.ctx.strokeStyle = "#06b6d4";
            this.ctx.shadowColor = "#38bdf8";
            this.ctx.beginPath();
            for (let x = 0; x < width; x++) {
                const progress = x / width;
                const envelope = Math.sin(progress * Math.PI);
                const y = centerY + Math.sin(x * 0.05 - time * 2.5) * 12 * envelope
                                  + Math.cos(x * 0.03 + time) * 6 * envelope;
                if (x === 0) this.ctx.moveTo(x, y);
                else this.ctx.lineTo(x, y);
            }
            this.ctx.stroke();

        } else if (this.analyser && (window.isRecording || window.isUserSpeakingInCall)) {
            // Usuario Hablando: Forma de onda en tiempo real desde el AnalyserNode
            const bufferLength = this.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            this.analyser.getByteTimeDomainData(dataArray);

            this.ctx.lineWidth = 2.5;
            this.ctx.strokeStyle = "#10b981"; // Esmeralda
            this.ctx.shadowBlur = 12;
            this.ctx.shadowColor = "#34d399";

            this.ctx.beginPath();
            const sliceWidth = width / bufferLength;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const v = dataArray[i] / 128.0;
                const progress = i / bufferLength;
                const envelope = Math.sin(progress * Math.PI);
                const y = centerY + (v - 1.0) * (height / 2) * 1.6 * envelope;

                if (i === 0) this.ctx.moveTo(x, y);
                else this.ctx.lineTo(x, y);

                x += sliceWidth;
            }
            this.ctx.lineTo(width, centerY);
            this.ctx.stroke();

        } else {
            // Reposo: Onda suave y sutil de respiración en azul
            const time = Date.now() * 0.002;
            this.ctx.lineWidth = 1.5;
            this.ctx.strokeStyle = "rgba(59, 130, 246, 0.45)";
            this.ctx.shadowBlur = 6;
            this.ctx.shadowColor = "rgba(59, 130, 246, 0.5)";

            this.ctx.beginPath();
            for (let x = 0; x < width; x++) {
                const progress = x / width;
                const envelope = Math.sin(progress * Math.PI);
                const y = centerY + Math.sin(x * 0.03 + time) * 5 * envelope;
                if (x === 0) this.ctx.moveTo(x, y);
                else this.ctx.lineTo(x, y);
            }
            this.ctx.stroke();
        }
    }
};

window.AudioVisualizer = AudioVisualizer;

