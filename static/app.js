// ==============================================================================
// Voice Assistant - Main Application Controller (Modular Orchestrator)
// ==============================================================================

// Estado Global de la Sesión
let socket = null;
let reconnectAttempts = 0;
let isCallMode = false;
let currentLanguageMode = "en";
let isWhisperMode = false;
let turnStartTime = 0;
let firstAudioReceived = false;

// Exponer variables reactivas a módulos hijos
Object.defineProperty(window, "isCallMode", { get: () => isCallMode, set: (v) => { isCallMode = v; } });
Object.defineProperty(window, "currentLanguageMode", { get: () => currentLanguageMode, set: (v) => { currentLanguageMode = v; } });
Object.defineProperty(window, "isWhisperMode", { get: () => isWhisperMode, set: (v) => { isWhisperMode = v; } });

// Referencias del DOM
const connectionStatus = document.getElementById("connection-status");
const statusText = document.getElementById("status-text");
const textInput = document.getElementById("text-input");
const sendBtn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");
const micBtnLabel = document.getElementById("mic-btn-label");
const callModeBtn = document.getElementById("call-mode-btn");
const callBtnText = document.getElementById("call-btn-text");
const interruptBtn = document.getElementById("interrupt-btn");
const micSelect = document.getElementById("mic-select");
const voiceSelect = document.getElementById("voice-select");
const vadSelect = document.getElementById("vad-select");
const personalitySelect = document.getElementById("personality-select");
const whisperBtn = document.getElementById("whisper-btn");
const whisperBtnLabel = document.getElementById("whisper-btn-label");
const micMeterContainer = document.getElementById("mic-meter-container");
const meterBarFill = document.getElementById("meter-bar-fill");
const meterThresholdLine = document.getElementById("meter-threshold-line");
const metricStt = document.getElementById("metric-stt");
const metricTts = document.getElementById("metric-tts");
const metricTotal = document.getElementById("metric-total");

// Instanciación de Gestores Modulares
const chatUI = new ChatUIManager();
const notesDrawer = new NotesDrawerManager();
const gpuTelemetry = new GpuTelemetryManager();

const audioPlayer = new AudioPlayerManager({
    onPlayStart: () => {
        if (interruptBtn) interruptBtn.classList.remove("hidden");
        chatUI.setOrbState("speaking", "Hablando...");
    },
    onPlayEnd: () => {
        if (interruptBtn) interruptBtn.classList.add("hidden");
        if (isCallMode) {
            chatUI.setOrbState("listening", "📞 Te escucho...");
        } else {
            chatUI.setOrbState("idle", "Listo para conversar");
        }
    },
    onInterrupt: () => {
        if (interruptBtn) interruptBtn.classList.add("hidden");
    }
});

const audioRecorder = new AudioRecorderManager({
    vadThreshold: 0.030,
    silenceTimeoutMs: 650,
    maxSpeechDurationMs: 7500,

    onSpeechStart: () => {
        chatUI.setOrbState("listening", "Escuchando...");
        if (audioPlayer.isAudioPlaying) {
            audioPlayer.interrupt();
            sendWsMessage({ type: "interrupt" });
        }
    },
    onSilenceDetected: (samples) => {
        chatUI.setOrbState("thinking", "Procesando respuesta...");
        sendWavBuffer(samples, "audio_final");
    },
    onPartialAudio: (samples) => {
        sendWavBuffer(samples, "audio_stream");
    },
    onMicLevel: (rms, isSpeaking) => {
        if (meterBarFill) {
            const visualPct = Math.min(100, Math.round(rms * 400));
            meterBarFill.style.width = visualPct + "%";
            meterBarFill.classList.toggle("speaking", isSpeaking);
        }
    },
    onSecureContextError: (httpsUrl) => {
        chatUI.showSecureContextModal(httpsUrl);
    }
});

// ==============================================================================
// 1. GESTIÓN DE WEBSOCKET (WSS SEGURO)
// ==============================================================================

function sendWsMessage(payload) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(payload));
    }
}

function sendWavBuffer(samples, messageType = "audio_final", turnId = null) {
    if (samples.length < 4000) return;
    const wavBlob = encodeWAV(samples, 16000);
    const reader = new FileReader();
    reader.readAsDataURL(wavBlob);
    reader.onloadend = () => {
        const base64Wav = reader.result.split(",")[1];
        const payload = { type: messageType, audio: base64Wav };
        if (messageType === "audio_final") {
            turnStartTime = Date.now();
            payload.turn_id = turnId || ("turn-" + turnStartTime);
            firstAudioReceived = false;
        }
        sendWsMessage(payload);
    };
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        reconnectAttempts = 0;
        if (connectionStatus) connectionStatus.className = "status-indicator connected";
        if (statusText) statusText.innerText = "Conectado (Local)";
        if (!isCallMode) chatUI.setOrbState("idle", "Listo para conversar");

        if (voiceSelect) sendWsMessage({ type: "set_voice", voice: voiceSelect.value });
        if (personalitySelect) sendWsMessage({ type: "set_personality", personality: personalitySelect.value });
        sendWsMessage({ type: "set_mode", mode: currentLanguageMode });
    };

    socket.onclose = () => {
        if (connectionStatus) connectionStatus.className = "status-indicator";
        if (statusText) statusText.innerText = "Desconectado. Reintentando...";
        chatUI.setOrbState("idle", "Reconectando...");
        const delay = Math.min(1000 * Math.pow(1.5, reconnectAttempts), 8000);
        reconnectAttempts++;
        setTimeout(connectWebSocket, delay);
    };

    socket.onerror = (err) => console.error("[WebSocket] Error:", err);

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };
}

function handleServerMessage(data) {
    switch (data.type) {
        case "status":
            if (data.state === "transcribing") {
                chatUI.setOrbState("thinking", "Transcribiendo tu voz...");
            } else if (data.state === "thinking") {
                chatUI.setOrbState("thinking", "Pensando respuesta...");
            } else if (data.state === "idle" && !audioPlayer.isAudioPlaying) {
                if (isCallMode) {
                    chatUI.setOrbState("listening", "📞 Llamada activa: habla cuando quieras");
                } else {
                    chatUI.setOrbState("idle", "Listo para conversar");
                }
            }
            break;

        case "user_partial_transcription":
            audioRecorder.isPartialSttPending = false;
            chatUI.updateUserPartialBubble(data.text, data.lang, currentLanguageMode);
            break;

        case "user_transcription":
            chatUI.createUserBubble(data.text || data.english, data.stt_ms, data.lang, data.turn_id, currentLanguageMode);
            if (data.stt_ms && metricStt) metricStt.innerText = `${data.stt_ms} ms`;
            break;

        case "tool_executed":
            chatUI.handleToolExecuted(data);
            if (data.tool === "save_voice_note") {
                notesDrawer.fetchNotes();
            }
            break;

        case "user_translation":
            chatUI.updateUserTranslation(data.translation || data.spanish, data.turn_id);
            break;

        case "coaching_feedback":
            chatUI.showCoachingTip(data.tip);
            break;

        case "ai_chunk":
            chatUI.appendAiChunk(data.delta, data.turn_id);
            break;

        case "audio_chunk":
            if (!firstAudioReceived && turnStartTime > 0) {
                const ttfa = Date.now() - turnStartTime;
                if (metricTts) metricTts.innerText = `${ttfa} ms`;
                const pill = document.getElementById(`ai-latency-${data.turn_id}`);
                if (pill) {
                    const val = pill.querySelector(".ttfa-val");
                    if (val) val.innerText = ttfa;
                    pill.classList.remove("hidden");
                }
                firstAudioReceived = true;
            }
            audioPlayer.enqueueAudio(data.audio);
            break;

        case "ai_done":
            if (turnStartTime > 0) {
                const totalSec = ((Date.now() - turnStartTime) / 1000).toFixed(2);
                if (metricTotal) metricTotal.innerText = `${totalSec} s`;
                const meta = document.getElementById(`ai-meta-${data.turn_id}`);
                if (meta) {
                    const totalVal = meta.querySelector(".total-time-val");
                    if (totalVal) totalVal.innerText = totalSec;
                    meta.classList.remove("hidden");
                }
            }
            break;

        case "ai_translation":
            chatUI.updateAiTranslation(data.translation || data.spanish, data.turn_id);
            break;

        case "voice_changed":
            if (voiceSelect) {
                if (currentLanguageMode === "es" && data.spanish_voice) {
                    voiceSelect.value = data.spanish_voice;
                } else if (currentLanguageMode === "en" && data.english_voice) {
                    voiceSelect.value = data.english_voice;
                }
            }
            break;

        case "whisper_mode_changed":
            isWhisperMode = !!data.enabled;
            if (whisperBtn) {
                whisperBtn.classList.toggle("active", isWhisperMode);
                whisperBtn.setAttribute("aria-pressed", isWhisperMode ? "true" : "false");
            }
            if (whisperBtnLabel && window.I18nManager) {
                whisperBtnLabel.innerText = isWhisperMode ?
                    (I18nManager.t("whisper_on") || "Activado") :
                    (I18nManager.t("whisper_off") || "Desactivado");
            }
            break;

        case "interrupted":
            audioPlayer.interrupt();
            chatUI.setOrbState(isCallMode ? "listening" : "idle", isCallMode ? "📞 Te escucho..." : "Interrumpido");
            break;

        case "error":
            chatUI.showSystemNotification(data.message);
            chatUI.setOrbState(isCallMode ? "listening" : "idle", isCallMode ? "📞 Te escucho..." : "Listo para conversar");
            break;
    }
}

// ==============================================================================
// 2. INICIALIZACIÓN DEL CONTROLADOR Y EVENT LISTENERS
// ==============================================================================

window.addEventListener("DOMContentLoaded", async () => {
    // 1. Registro de Service Worker PWA para soporte móvil nativo
    if ('serviceWorker' in navigator && (window.location.protocol === 'https:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
        navigator.serviceWorker.register('/static/sw.js')
            .then(() => console.log('✓ Service Worker PWA activo'))
            .catch((err) => console.debug('Service Worker info:', err));
    }

    // 2. Inicializar i18n y Telemetría
    if (window.I18nManager) await window.I18nManager.init();
    connectWebSocket();
    gpuTelemetry.startPolling(4500);
    notesDrawer.fetchNotes();

    if (window.AudioVisualizer) window.AudioVisualizer.init();
    audioRecorder.populateMicrophones(micSelect);

    // 3. Marcador VAD
    function updateThresholdMarker() {
        if (meterThresholdLine) {
            const threshPct = Math.min(95, Math.max(5, Math.round(audioRecorder.vadThreshold * 400)));
            meterThresholdLine.style.left = threshPct + "%";
        }
    }

    if (vadSelect) {
        vadSelect.value = audioRecorder.vadThreshold.toString();
        updateThresholdMarker();
        vadSelect.addEventListener("change", () => {
            audioRecorder.setVadThreshold(vadSelect.value);
            updateThresholdMarker();
        });
    }

    // 4. Selectores de Voz, Personalidad y Modo Susurro
    if (voiceSelect) {
        voiceSelect.addEventListener("change", () => {
            sendWsMessage({ type: "set_voice", voice: voiceSelect.value });
        });
    }

    if (personalitySelect) {
        personalitySelect.addEventListener("change", () => {
            sendWsMessage({ type: "set_personality", personality: personalitySelect.value });
        });
    }

    if (whisperBtn) {
        whisperBtn.addEventListener("click", () => {
            const nextState = !isWhisperMode;
            sendWsMessage({ type: "set_whisper_mode", enabled: nextState });
        });
    }

    // 5. Selector de Modo de Idioma
    document.querySelectorAll(".lang-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentLanguageMode = btn.dataset.mode;

            if (window.I18nManager) {
                if (currentLanguageMode === "es") {
                    window.I18nManager.setLanguage("es", false);
                } else if (currentLanguageMode === "en") {
                    window.I18nManager.setLanguage("en", false);
                } else {
                    window.I18nManager.applyLanguage(window.I18nManager.currentLang);
                }
            }

            if (voiceSelect && !voiceSelect.value.startsWith("blend_")) {
                if (currentLanguageMode === "es") voiceSelect.value = "ef_dora";
                else if (currentLanguageMode === "en") voiceSelect.value = "af_sarah";
                sendWsMessage({ type: "set_voice", voice: voiceSelect.value });
            }

            sendWsMessage({ type: "set_mode", mode: currentLanguageMode });
        });
    });

    // 6. Selector de Idioma de UI Global
    const uiLangSelect = document.getElementById("ui-lang-select");
    if (uiLangSelect && window.I18nManager) {
        uiLangSelect.value = window.I18nManager.currentLang;
        uiLangSelect.addEventListener("change", (e) => {
            window.I18nManager.setLanguage(e.target.value, true);
        });
    }

    // 7. Botón Interrumpir (Barge-in manual)
    if (interruptBtn) {
        interruptBtn.addEventListener("click", () => {
            audioPlayer.interrupt();
            sendWsMessage({ type: "interrupt" });
        });
    }

    // 8. Botón Modo Llamada Manos Libres (Full-Duplex)
    if (callModeBtn) {
        callModeBtn.addEventListener("click", async () => {
            isCallMode = !isCallMode;
            if (isCallMode) {
                const ready = await audioRecorder.setupAudioStream(micSelect ? micSelect.value : "");
                if (!ready) {
                    isCallMode = false;
                    return;
                }
                callModeBtn.classList.add("active");
                if (callBtnText) callBtnText.innerText = "Finalizar Llamada";
                if (micMeterContainer) micMeterContainer.classList.remove("hidden");
                chatUI.setOrbState("listening", "📞 Llamada activa: habla cuando quieras");
            } else {
                callModeBtn.classList.remove("active");
                if (callBtnText) callBtnText.innerText = "Iniciar Modo Llamada";
                if (micMeterContainer) micMeterContainer.classList.add("hidden");
                chatUI.setOrbState("idle", "Llamada finalizada");
                audioPlayer.interrupt();
            }
        });
    }

    // 9. Botón Grabar / Push-to-Talk Manual
    if (micBtn) {
        micBtn.addEventListener("click", async () => {
            if (isCallMode) return;
            if (!audioRecorder.isRecording) {
                const ready = await audioRecorder.setupAudioStream(micSelect ? micSelect.value : "");
                if (!ready) return;
                audioRecorder.startManualRecording();
                micBtn.classList.add("recording");
                if (micBtnLabel) micBtnLabel.innerText = "Detener";
                chatUI.setOrbState("listening", "Escuchando...");
            } else {
                const samples = audioRecorder.stopManualRecording();
                micBtn.classList.remove("recording");
                if (micBtnLabel) micBtnLabel.innerText = "Hablar";
                chatUI.setOrbState("thinking", "Procesando respuesta...");
                sendWavBuffer(samples, "audio_final");
            }
        });
    }

    // 10. Envío de Mensajes por Texto
    function handleSendText() {
        if (!textInput) return;
        const text = textInput.value.trim();
        if (!text) return;
        const turnId = "turn-" + Date.now();
        turnStartTime = Date.now();
        firstAudioReceived = false;

        chatUI.createUserBubble(text, null, currentLanguageMode, turnId, currentLanguageMode);
        chatUI.setOrbState("thinking", "Pensando respuesta...");

        sendWsMessage({ type: "text", text: text, turn_id: turnId });
        textInput.value = "";
    }

    if (sendBtn) sendBtn.addEventListener("click", handleSendText);
    if (textInput) {
        textInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendText();
            }
        });
    }

    // 11. Botón Exportar Sesión a Markdown
    const exportBtn = document.getElementById("export-session-btn");
    if (exportBtn) {
        exportBtn.addEventListener("click", () => chatUI.exportSessionToMarkdown());
    }

    // 12. Botón Limpiar Historial Completo
    const clearHistoryBtn = document.getElementById("clear-history-btn");
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener("click", async () => {
            const confirmMsg = window.I18nManager ? window.I18nManager.t("clear_confirm") : "¿Deseas vaciar la base de datos de conversaciones, notas y vocabulario guardado?";
            if (confirm(confirmMsg)) {
                try {
                    await fetch("/api/history", { method: "DELETE" });
                    notesDrawer.fetchNotes();
                    if (chatUI.chatMessages) chatUI.chatMessages.innerHTML = '';
                    if (chatUI.vocabularyList) chatUI.vocabularyList.innerHTML = '<div class="empty-tip">Historial limpiado.</div>';
                } catch (err) {
                    console.error("Error al limpiar historial:", err);
                }
            }
        });
    }
});
