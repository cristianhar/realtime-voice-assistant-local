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
const speedSelect = document.getElementById("speed-select");
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
const earcons = new EarconManager();

let currentSessionId = `sess-${Math.floor(Date.now() / 1000)}`;

const historyDrawer = new HistoryDrawerManager({}, {
    initialSessionId: currentSessionId,
    onSwitchSession: (sessionId, messages) => {
        currentSessionId = sessionId;
        chatUI.loadHistoricalMessages(messages, currentLanguageMode);
        sendWsMessage({ type: "switch_session", session_id: sessionId });
        chatUI.setOrbState("idle", "Conversación cargada");
    },
    onNewChat: (newSessionId, title) => {
        currentSessionId = newSessionId;
        chatUI.clearMessages();
        sendWsMessage({ type: "switch_session", session_id: newSessionId });
        chatUI.setOrbState("idle", "Nueva conversación lista");
    }
});
window.historyDrawer = historyDrawer;

const audioPlayer = new AudioPlayerManager({
    onPlayStart: () => {
        if (interruptBtn) {
            interruptBtn.classList.remove("hidden");
            const parent = interruptBtn.closest(".action-btn-interrupt");
            if (parent) parent.classList.remove("hidden");
        }
        chatUI.setOrbState("speaking", "Hablando...");
    },
    onPlayEnd: () => {
        if (interruptBtn) {
            interruptBtn.classList.add("hidden");
            const parent = interruptBtn.closest(".action-btn-interrupt");
            if (parent) parent.classList.add("hidden");
        }
        if (audioPlayer.activeTurnId) {
            chatUI.finalizeAiTurn(audioPlayer.activeTurnId);
        }
        if (isCallMode) {
            chatUI.setOrbState("listening", "📞 Te escucho...");
        } else {
            chatUI.setOrbState("idle", "Listo para conversar");
        }
    },
    onChunkStart: (text, turnId, audioObj) => {
        chatUI.revealChunkSpeech(text, turnId, audioObj);
    },
    onInterrupt: () => {
        chatUI.interruptSpeechSync();
        if (interruptBtn) {
            interruptBtn.classList.add("hidden");
            const parent = interruptBtn.closest(".action-btn-interrupt");
            if (parent) parent.classList.add("hidden");
        }
    }
});

const audioRecorder = new AudioRecorderManager({
    vadThreshold: 0.030,
    silenceTimeoutMs: 650,
    maxSpeechDurationMs: 7500,

    onSpeechStart: () => {
        chatUI.setOrbState("listening", "Escuchando...");
        if (audioPlayer.isAudioPlaying || audioPlayer.isPlayingAudioNow() || audioPlayer.activeTurnId) {
            const currentTid = audioPlayer.activeTurnId;
            audioPlayer.interrupt(currentTid);
            sendWsMessage({ type: "interrupt", turn_id: currentTid });
            earcons.playBargeIn();
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
            const tid = turnId || ("turn-" + turnStartTime);
            payload.turn_id = tid;
            audioPlayer.startTurn(tid);
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
            } else if (data.state === "idle" && !audioPlayer.isAudioPlaying && !audioPlayer.activeTurnId) {
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
            earcons.playToolSuccess();
            chatUI.handleToolExecuted(data);
            if (data.tool === "save_voice_note") {
                notesDrawer.fetchNotes();
            } else if (data.tool === "set_speech_speed" && data.data && data.data.speed) {
                const newSpeed = parseFloat(data.data.speed);
                audioPlayer.setPlaybackSpeed(newSpeed);
                if (speedSelect) speedSelect.value = newSpeed.toString();
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
            audioPlayer.enqueueAudio(data.audio, data.turn_id, data.text || "");
            break;

        case "ai_done":
            audioPlayer.markTurnComplete(data.turn_id);
            if (!audioPlayer.isPlayingAudioNow() && audioPlayer.audioQueue.length === 0) {
                chatUI.finalizeAiTurn(data.turn_id, data.full_text);
            }
            if (data.turn_id && data.full_text) {
                const aiTextEl = document.getElementById(`ai-text-${data.turn_id}`);
                if (aiTextEl && !aiTextEl.innerText.trim()) {
                    aiTextEl.innerText = data.full_text;
                }
            }
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

        case "ai_interrupted":
            audioPlayer.interrupt(data.turn_id);
            if (data.turn_id && data.partial_text) {
                const aiTextEl = document.getElementById(`ai-text-${data.turn_id}`);
                if (aiTextEl) {
                    aiTextEl.innerText = data.partial_text;
                }
                chatUI.finalizeAiTurn(data.turn_id, data.partial_text);
            }
            chatUI.setOrbState(isCallMode ? "listening" : "idle", isCallMode ? "📞 Te escucho..." : "Interrumpido");
            break;

        case "session_switched":
            currentSessionId = data.session_id;
            if (window.historyDrawer) {
                window.historyDrawer.setActiveSession(data.session_id);
            }
            break;

        case "title_generated":
            console.log(`[AutoTitling] Título generado por IA: ${data.title} para sesión ${data.session_id}`);
            if (window.historyDrawer) {
                window.historyDrawer.onTitleGenerated(data.session_id, data.title);
            }
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
    historyDrawer.fetchSessions();

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

    if (speedSelect) {
        speedSelect.addEventListener("change", () => {
            const val = parseFloat(speedSelect.value);
            audioPlayer.setPlaybackSpeed(val);
        });
    }

    if (whisperBtn) {
        whisperBtn.addEventListener("click", () => {
            const nextState = !isWhisperMode;
            sendWsMessage({ type: "set_whisper_mode", enabled: nextState });
        });
    }

    // Toggle de Sincronización de Texto y Voz (Karaoke / Teleprompter)
    const toggleSyncText = document.getElementById("toggle-sync-text");
    const savedSyncPref = localStorage.getItem("voice_assistant_sync_text");
    const initialSyncState = savedSyncPref !== null ? (savedSyncPref === "true") : true;

    chatUI.setSyncTextEnabled(initialSyncState);
    if (toggleSyncText) {
        toggleSyncText.checked = initialSyncState;
        toggleSyncText.addEventListener("change", (e) => {
            const isChecked = e.target.checked;
            chatUI.setSyncTextEnabled(isChecked);
            localStorage.setItem("voice_assistant_sync_text", isChecked ? "true" : "false");
            console.log(`[TextSync] Sincronización de texto con habla: ${isChecked ? 'ACTIVADA' : 'DESACTIVADA'}`);
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

    // 6.1 Popover de Información del Sistema (!) en Header
    const btnInfoModal = document.getElementById("btn-info-modal");
    const systemInfoPopover = document.getElementById("system-info-popover");
    const btnClosePopover = document.getElementById("btn-close-popover");

    if (btnInfoModal && systemInfoPopover) {
        btnInfoModal.addEventListener("click", (e) => {
            e.stopPropagation();
            systemInfoPopover.classList.toggle("hidden");
        });

        if (btnClosePopover) {
            btnClosePopover.addEventListener("click", () => {
                systemInfoPopover.classList.add("hidden");
            });
        }

        document.addEventListener("click", (e) => {
            if (!systemInfoPopover.contains(e.target) && !btnInfoModal.contains(e.target)) {
                systemInfoPopover.classList.add("hidden");
            }
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !systemInfoPopover.classList.contains("hidden")) {
                systemInfoPopover.classList.add("hidden");
            }
        });
    }

    // 6.1.1 Popover de Ayuda & Bienvenida (?) en Header
    const btnHelpModal = document.getElementById("btn-help-modal");
    const welcomeHelpPopover = document.getElementById("welcome-help-popover");
    const btnCloseHelp = document.getElementById("btn-close-help");

    if (btnHelpModal && welcomeHelpPopover) {
        btnHelpModal.addEventListener("click", (e) => {
            e.stopPropagation();
            welcomeHelpPopover.classList.toggle("hidden");
        });

        if (btnCloseHelp) {
            btnCloseHelp.addEventListener("click", () => {
                welcomeHelpPopover.classList.add("hidden");
            });
        }

        document.addEventListener("click", (e) => {
            if (!welcomeHelpPopover.contains(e.target) && !btnHelpModal.contains(e.target)) {
                welcomeHelpPopover.classList.add("hidden");
            }
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !welcomeHelpPopover.classList.contains("hidden")) {
                welcomeHelpPopover.classList.add("hidden");
            }
        });
    }

    // 6.2 Modal de Configuración de Audio & Voz (Apertura y Cierre)
    const btnAudioSettings = document.getElementById("btn-audio-settings");
    const btnDockSettings = document.getElementById("btn-dock-settings");
    const settingsModalOverlay = document.getElementById("settings-modal-overlay");
    const btnCloseSettings = document.getElementById("btn-close-settings");
    const btnSaveSettings = document.getElementById("btn-save-settings");

    function openSettingsModal() {
        if (settingsModalOverlay) settingsModalOverlay.classList.remove("hidden");
    }

    function closeSettingsModal() {
        if (settingsModalOverlay) settingsModalOverlay.classList.add("hidden");
    }

    if (btnAudioSettings) btnAudioSettings.addEventListener("click", openSettingsModal);
    if (btnDockSettings) btnDockSettings.addEventListener("click", openSettingsModal);
    if (btnCloseSettings) btnCloseSettings.addEventListener("click", closeSettingsModal);
    if (btnSaveSettings) btnSaveSettings.addEventListener("click", closeSettingsModal);

    if (settingsModalOverlay) {
        settingsModalOverlay.addEventListener("click", (e) => {
            if (e.target === settingsModalOverlay) {
                closeSettingsModal();
            }
        });
    }

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && settingsModalOverlay && !settingsModalOverlay.classList.contains("hidden")) {
            closeSettingsModal();
        }
    });

    // 7. Botón Interrumpir (Barge-in manual)
    if (interruptBtn) {
        interruptBtn.addEventListener("click", () => {
            audioPlayer.interrupt();
            sendWsMessage({ type: "interrupt" });
            earcons.playBargeIn();
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
                earcons.playCallStart();
                callModeBtn.classList.add("active");
                if (callBtnText) callBtnText.innerText = "Finalizar Llamada";
                if (micMeterContainer) micMeterContainer.classList.remove("hidden");
                chatUI.setOrbState("listening", "📞 Llamada activa: habla cuando quieras");
            } else {
                earcons.playCallEnd();
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
        audioPlayer.startTurn(turnId);

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
