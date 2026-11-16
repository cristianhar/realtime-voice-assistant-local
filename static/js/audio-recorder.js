// ==============================================================================
// Voice Assistant - Audio Recorder & VAD Engine (Web Audio API & Anti-Breath)
// ==============================================================================

class AudioRecorderManager {
    constructor(options = {}) {
        this.audioContext = null;
        this.mediaStream = null;
        this.scriptProcessor = null;
        this.audioSamples = [];
        this.callAudioBuffer = [];
        this.isRecording = false;

        this.vadThreshold = options.vadThreshold || 0.030;
        this.silenceTimeoutMs = options.silenceTimeoutMs || 650;
        this.maxSpeechDurationMs = options.maxSpeechDurationMs || 7500;

        this.isUserSpeakingInCall = false;
        this.callSilenceTimer = null;
        this.speechStartTime = 0;
        this.lastPartialSendTime = 0;
        this.isPartialSttPending = false;

        this.onSpeechStart = options.onSpeechStart || (() => {});
        this.onSilenceDetected = options.onSilenceDetected || (() => {});
        this.onPartialAudio = options.onPartialAudio || (() => {});
        this.onMicLevel = options.onMicLevel || (() => {});
        this.onSecureContextError = options.onSecureContextError || (() => {});
    }

    setVadThreshold(val) {
        this.vadThreshold = parseFloat(val);
    }

    async populateMicrophones(selectEl) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices || !selectEl) return;
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioInputs = devices.filter(d => d.kind === "audioinput");
            if (audioInputs.length === 0) return;

            selectEl.innerHTML = "";
            let preferredIndex = 0;

            audioInputs.forEach((device, index) => {
                const opt = document.createElement("option");
                opt.value = device.deviceId;
                opt.innerText = device.label || `Micrófono ${index + 1}`;

                const labelLow = (device.label || "").toLowerCase();
                if (labelLow.includes("headset") || labelLow.includes("micrófono") || labelLow.includes("sz01")) {
                    if (!labelLow.includes("cable") && !labelLow.includes("virtual")) {
                        preferredIndex = index;
                    }
                }
                selectEl.appendChild(opt);
            });

            selectEl.selectedIndex = preferredIndex;
        } catch (e) {
            console.warn("[AudioRecorder] Error enumerando micrófonos:", e);
        }
    }

    async setupAudioStream(deviceId = "") {
        if (this.mediaStream && this.audioContext) return true;

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
            if (window.location.protocol === "http:" && !isLocal) {
                const httpsUrl = `https://${window.location.hostname}:8000`;
                this.onSecureContextError(httpsUrl);
                return false;
            }
            return false;
        }

        try {
            const audioConstraints = {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            };
            if (deviceId) {
                audioConstraints.deviceId = { exact: deviceId };
            }

            this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.micAnalyser = this.audioContext.createAnalyser();
            this.micAnalyser.fftSize = 256;
            source.connect(this.micAnalyser);

            if (window.AudioVisualizer) {
                window.AudioVisualizer.setAnalyser(this.micAnalyser);
            }

            const gainNode = this.audioContext.createGain();
            gainNode.gain.value = 1.0;

            this.scriptProcessor = this.audioContext.createScriptProcessor(4096, 1, 1);
            this.scriptProcessor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);

                if (this.isRecording) {
                    this.audioSamples.push(...inputData);
                }

                if (window.isCallMode) {
                    this.handleCallModeAudio(inputData);
                }
            };

            source.connect(gainNode);
            gainNode.connect(this.scriptProcessor);
            this.scriptProcessor.connect(this.audioContext.destination);

            return true;
        } catch (e) {
            console.error("[AudioRecorder] Error al configurar micrófono:", e);
            return false;
        }
    }

    handleCallModeAudio(inputData) {
        let sum = 0;
        let zeroCrossings = 0;
        for (let i = 0; i < inputData.length; i++) {
            sum += inputData[i] * inputData[i];
            if (i > 0 && ((inputData[i] >= 0 && inputData[i-1] < 0) || (inputData[i] < 0 && inputData[i-1] >= 0))) {
                zeroCrossings++;
            }
        }
        const rms = Math.sqrt(sum / inputData.length);
        const zcr = zeroCrossings / inputData.length;

        // Análisis espectral de formantes vocales vs ruido parásito (respiración / clics de teclado)
        let isVoiceFormant = true;
        if (this.micAnalyser) {
            if (!this.freqData) this.freqData = new Uint8Array(this.micAnalyser.frequencyBinCount);
            this.micAnalyser.getByteFrequencyData(this.freqData);

            let subBassEnergy = 0;   // < 125 Hz (viento, soplido, choque de aire)
            let voiceEnergy = 0;    // 250 Hz - 3000 Hz (formantes vocales F1-F3)
            let highClickEnergy = 0; // > 4000 Hz (teclado mecánico, chasquidos)

            for (let b = 0; b <= 1; b++) subBassEnergy += this.freqData[b];
            for (let b = 4; b <= 48; b++) voiceEnergy += this.freqData[b];
            for (let b = 64; b < this.freqData.length; b++) highClickEnergy += this.freqData[b];

            const total = subBassEnergy + voiceEnergy + highClickEnergy + 1;
            // Filtrar soplido de respiración directo al micrófono
            if (subBassEnergy / total > 0.78 && voiceEnergy / total < 0.18) {
                isVoiceFormant = false;
            }
            // Filtrar ruidos impulsivos de teclado mecánico (>4 kHz con alto ZCR)
            else if (highClickEnergy / total > 0.65 && zcr > 0.30) {
                isVoiceFormant = false;
            }
        }

        const isSpeaking = (rms > this.vadThreshold) && (zcr < 0.38) && isVoiceFormant;

        this.onMicLevel(rms, isSpeaking);

        if (isSpeaking) {
            if (!this.isUserSpeakingInCall) {
                this.isUserSpeakingInCall = true;
                window.isUserSpeakingInCall = true;
                this.speechStartTime = Date.now();
                this.lastPartialSendTime = Date.now();
                this.callAudioBuffer = [];
                this.onSpeechStart();
            }

            if (this.callSilenceTimer) {
                clearTimeout(this.callSilenceTimer);
                this.callSilenceTimer = null;
            }

            this.callAudioBuffer.push(...inputData);

            const speechDuration = Date.now() - this.speechStartTime;
            if (speechDuration >= this.maxSpeechDurationMs) {
                this.finalizeCallUtterance();
                return;
            }

            const now = Date.now();
            if (now - this.lastPartialSendTime >= 350 && !this.isPartialSttPending) {
                this.lastPartialSendTime = now;
                this.isPartialSttPending = true;
                this.onPartialAudio(this.callAudioBuffer.slice());
            }
        } else if (this.isUserSpeakingInCall) {
            this.callAudioBuffer.push(...inputData);
            if (!this.callSilenceTimer) {
                this.callSilenceTimer = setTimeout(() => {
                    this.finalizeCallUtterance();
                }, this.silenceTimeoutMs);
            }
        }
    }

    finalizeCallUtterance() {
        if (!this.isUserSpeakingInCall) return;
        this.isUserSpeakingInCall = false;
        window.isUserSpeakingInCall = false;

        if (this.callSilenceTimer) {
            clearTimeout(this.callSilenceTimer);
            this.callSilenceTimer = null;
        }

        const samplesToEmit = this.callAudioBuffer.slice();
        this.callAudioBuffer = [];

        if (samplesToEmit.length >= 4000) {
            this.onSilenceDetected(samplesToEmit);
        }
    }

    startManualRecording() {
        this.audioSamples = [];
        this.isRecording = true;
        window.isRecording = true;
    }

    stopManualRecording() {
        this.isRecording = false;
        window.isRecording = false;
        const samples = this.audioSamples.slice();
        this.audioSamples = [];
        return samples;
    }
}

window.AudioRecorderManager = AudioRecorderManager;

