// Voice Assistant - Client Logic (Call Mode + Real-Time Live STT + Multi-Turn Sync + Streaming)

let socket = null;
let audioContext = null;
let mediaStream = null;
let scriptProcessor = null;
let audioSamples = [];
let isRecording = false;

// Estado del Modo Llamada Manos Libres (Full-Duplex)
let isCallMode = false;
let isUserSpeakingInCall = false;
let callAudioBuffer = [];
let callSilenceTimer = null;
let lastPartialSendTime = 0;
let isPartialSttPending = false;
let currentLanguageMode = "en"; // "en" | "es" | "auto"
let VAD_THRESHOLD = 0.030; // Sensibilidad de detección de voz (calibrada para ignorar respiraciones)
const SILENCE_TIMEOUT_MS = 650; // 650ms de silencio indican fin de frase
const MAX_SPEECH_DURATION_MS = 7500; // Máximo 7.5s continuos para evitar buffers colgados por respiración
let speechStartTime = 0;

// Cola de audio para reproducción en streaming
const audioQueue = [];
let isAudioPlaying = false;
let currentAudioElement = null;

// Elementos del DOM
const connectionStatus = document.getElementById("connection-status");
const statusText = document.getElementById("status-text");
const voiceOrb = document.getElementById("voice-orb");
const orbLabel = document.getElementById("orb-label");
const chatMessages = document.getElementById("chat-messages");
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
const coachingContent = document.getElementById("coaching-content");
const vocabularyList = document.getElementById("vocabulary-list");
const metricStt = document.getElementById("metric-stt");
const metricTts = document.getElementById("metric-tts");
const metricTime = document.getElementById("metric-time");
const metricTotal = document.getElementById("metric-total");

let turnStartTime = 0;
let firstAudioReceived = false;
let peakRmsObserved = 0;
let isWhisperMode = false;

let currentPartialBubble = null;
let currentPartialTextEl = null;

// Exponer variables reactivas al entorno modular (AudioVisualizer & I18nManager)
Object.defineProperty(window, "isAudioPlaying", { get: () => isAudioPlaying, set: (v) => { isAudioPlaying = v; } });
Object.defineProperty(window, "isRecording", { get: () => isRecording, set: (v) => { isRecording = v; } });
Object.defineProperty(window, "isCallMode", { get: () => isCallMode, set: (v) => { isCallMode = v; } });
Object.defineProperty(window, "isUserSpeakingInCall", { get: () => isUserSpeakingInCall, set: (v) => { isUserSpeakingInCall = v; } });
Object.defineProperty(window, "currentLanguageMode", { get: () => currentLanguageMode, set: (v) => { currentLanguageMode = v; } });
Object.defineProperty(window, "isWhisperMode", { get: () => isWhisperMode, set: (v) => { isWhisperMode = v; } });

// ==========================================
// INTERNACIONALIZACIÓN Y MULTIIDIOMA UI (i18n)
// Delegado a static/js/i18n.js y static/locales.json
// ==========================================
function setUiLanguage(lang) {
    if (window.I18nManager) {
        window.I18nManager.setLanguage(lang);
    }
}

function getFormattedTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

let reconnectAttempts = 0;

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        reconnectAttempts = 0;
        connectionStatus.className = "status-indicator connected";
        statusText.innerText = "Conectado (Local)";
        if (!isCallMode) setOrbState("idle", "Listo para conversar");
        if (voiceSelect) {
            socket.send(JSON.stringify({
                type: "set_voice",
                voice: voiceSelect.value
            }));
        }
        if (personalitySelect) {
            socket.send(JSON.stringify({
                type: "set_personality",
                personality: personalitySelect.value
            }));
        }
        socket.send(JSON.stringify({
            type: "set_mode",
            mode: currentLanguageMode
        }));
    };

    socket.onclose = () => {
        connectionStatus.className = "status-indicator";
        statusText.innerText = "Desconectado. Reintentando...";
        setOrbState("idle", "Reconectando...");
        const delay = Math.min(1000 * Math.pow(1.5, reconnectAttempts), 8000);
        reconnectAttempts++;
        setTimeout(connectWebSocket, delay);
    };

    socket.onerror = (err) => {
        console.error("Error en WebSocket:", err);
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };
}

function setOrbState(state, label) {
    voiceOrb.className = `voice-orb ${state}`;
    if (label) orbLabel.innerText = label;
}

function handleServerMessage(data) {
    switch (data.type) {
        case "status":
            if (data.state === "transcribing") {
                setOrbState("thinking", "Transcribiendo tu voz...");
            } else if (data.state === "thinking") {
                setOrbState("thinking", "Pensando respuesta...");
            } else if (data.state === "idle" && !isAudioPlaying) {
                if (isCallMode) {
                    setOrbState("listening", "📞 Llamada activa: habla cuando quieras");
                } else {
                    setOrbState("idle", "Listo para conversar");
                }
            }
            break;

        case "user_partial_transcription":
            isPartialSttPending = false;
            updateUserPartialBubble(data.text, data.lang);
            break;

        case "user_transcription":
            createUserBubble(data.text || data.english, data.stt_ms, data.lang, data.turn_id);
            if (data.stt_ms) {
                metricStt.innerText = `${data.stt_ms} ms`;
            }
            break;

        case "tool_executed":
            handleToolExecuted(data);
            break;

        case "user_translation":
            updateUserTranslation(data.translation || data.spanish, data.turn_id);
            break;

        case "coaching_feedback":
            showCoachingTip(data.tip);
            break;

        case "ai_chunk":
            appendAiChunk(data.delta, data.turn_id);
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
            enqueueAudio(data.audio);
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
            updateAiTranslation(data.translation || data.spanish, data.turn_id);
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
            isPartialSttPending = false;
            stopAudioPlayback();
            if (isCallMode) {
                setOrbState("listening", "📞 Te escucho...");
            } else {
                setOrbState("idle", "Interrumpido");
            }
            break;

        case "error":
            isPartialSttPending = false;
            showSystemNotification(data.message);
            if (isCallMode) {
                setOrbState("listening", "📞 Te escucho...");
            } else {
                setOrbState("idle", "Listo para conversar");
            }
            break;
    }
}

function showSystemNotification(msg) {
    const notice = document.createElement("div");
    notice.style.padding = "10px 16px";
    notice.style.margin = "8px auto";
    notice.style.maxWidth = "80%";
    notice.style.borderRadius = "8px";
    notice.style.backgroundColor = "rgba(239, 68, 68, 0.2)";
    notice.style.border = "1px solid #ef4444";
    notice.style.color = "#fca5a5";
    notice.style.fontSize = "0.88rem";
    notice.style.textAlign = "center";
    notice.innerText = `⚠️ ${msg}`;
    chatMessages.appendChild(notice);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showSecureContextModal(httpsUrl) {
    if (document.getElementById("secure-context-alert")) {
        const el = document.getElementById("secure-context-alert");
        el.scrollIntoView({ behavior: "smooth" });
        return;
    }

    const card = document.createElement("div");
    card.id = "secure-context-alert";
    card.className = "secure-context-card";
    card.innerHTML = `
        <div class="secure-context-header">
            <span class="secure-icon" style="font-size: 1.4rem;">🔒</span>
            <strong>Micrófono bloqueado por Chrome en tu Celular</strong>
        </div>
        <p class="secure-context-desc">
            Por política de seguridad de Google y Apple, los celulares <b>bloquean el micrófono en páginas HTTP por red local</b>. Para hablar con tu voz debes entrar por <b>HTTPS</b>:
        </p>
        <div class="secure-context-actions">
            <a href="${httpsUrl}" class="secure-btn-primary">
                🚀 Entrar con HTTPS (${httpsUrl})
            </a>
        </div>
        <div class="secure-context-help">
            <strong>📋 Pasos para entrar (Solo toma 5 segundos):</strong><br>
            1. Toca el botón azul de arriba.<br>
            2. En Chrome te saldrá <i>"La conexión no es privada"</i>.<br>
            3. Toca en <b>"Configuración avanzada"</b> (abajo) y luego en <b>"Acceder a ${window.location.hostname} (no seguro)"</b>.<br>
            4. ¡Listo! El micrófono se activará de inmediato.
        </div>
        <div class="secure-context-alt">
            💡 <b>Alternativa sin HTTPS (Chrome Android):</b><br>
            Abre una pestaña con <code>chrome://flags/#unsafely-treat-insecure-origin-as-secure</code>, pega <code>${window.location.origin}</code>, marca <i>Enabled</i> y reinicia Chrome.
        </div>
    `;

    chatMessages.appendChild(card);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ==========================================
// RENDERIZADO EN VIVO DE TRANSCRIPCIÓN
// ==========================================

function updateUserPartialBubble(partialText, lang) {
    if (!currentPartialBubble) {
        const timeStr = getFormattedTime();
        if (metricTime) metricTime.innerText = timeStr;

        currentPartialBubble = document.createElement("div");
        currentPartialBubble.className = "message-bubble user partial";

        let roleLabel = "👤 You (English)";
        if (currentLanguageMode === "es") {
            roleLabel = "👤 Tú (Español)";
        } else if (currentLanguageMode === "auto") {
            roleLabel = `👤 You / Tú [${lang ? lang.toUpperCase() : "AUTO"}]`;
        }

        currentPartialBubble.innerHTML = `
            <div class="bubble-header">
                <span class="bubble-role">${roleLabel}</span>
                <span class="bubble-time">${timeStr} <span class="live-dot">● En vivo</span></span>
            </div>
            <div class="bubble-text-en"></div>
        `;
        chatMessages.appendChild(currentPartialBubble);
        currentPartialTextEl = currentPartialBubble.querySelector(".bubble-text-en");
    }

    if (currentPartialTextEl) {
        currentPartialTextEl.innerText = partialText + " ...";
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function createUserBubble(text, latency, lang, turnId) {
    const timeStr = getFormattedTime();
    if (metricTime) metricTime.innerText = timeStr;
    firstAudioReceived = false;

    const showTranslation = currentLanguageMode === "en";

    let roleLabel = "👤 You (English)";
    if (currentLanguageMode === "es") {
        roleLabel = "👤 Tú (Español)";
    } else if (currentLanguageMode === "auto") {
        roleLabel = `👤 You / Tú [${lang ? lang.toUpperCase() : "AUTO"}]`;
    }

    let bubble = currentPartialBubble;

    if (bubble) {
        bubble.classList.remove("partial");
        bubble.id = `user-bubble-${turnId}`;
        bubble.innerHTML = `
            <div class="bubble-header">
                <span class="bubble-role">${roleLabel}</span>
                <span class="bubble-time">${timeStr}</span>
            </div>
            <div class="bubble-text-en">${escapeHtml(text)}</div>
            ${showTranslation ? `<div class="bubble-text-es"><span>🇪🇸</span> <span id="user-tr-${turnId}" class="translation-placeholder">Traduciendo...</span></div>` : ""}
            ${latency ? `<div class="bubble-meta"><span>🎙️ STT: ${latency} ms</span></div>` : ""}
        `;
    } else {
        bubble = document.createElement("div");
        bubble.className = "message-bubble user";
        bubble.id = `user-bubble-${turnId}`;
        bubble.innerHTML = `
            <div class="bubble-header">
                <span class="bubble-role">${roleLabel}</span>
                <span class="bubble-time">${timeStr}</span>
            </div>
            <div class="bubble-text-en">${escapeHtml(text)}</div>
            ${showTranslation ? `<div class="bubble-text-es"><span>🇪🇸</span> <span id="user-tr-${turnId}" class="translation-placeholder">Traduciendo...</span></div>` : ""}
            ${latency ? `<div class="bubble-meta"><span>🎙️ STT: ${latency} ms</span></div>` : ""}
        `;
        chatMessages.appendChild(bubble);
    }

    currentPartialBubble = null;
    currentPartialTextEl = null;

    chatMessages.scrollTop = chatMessages.scrollHeight;
    addToVocabulary(text);

    // Burbuja de la IA asignada a este Turn ID específico
    let aiRoleLabel = "🤖 AI Tutor (English)";
    if (currentLanguageMode === "es") {
        aiRoleLabel = "🤖 Asistente (Español)";
    } else if (currentLanguageMode === "auto") {
        aiRoleLabel = "🤖 AI (Bilingual)";
    }

    const aiBubble = document.createElement("div");
    aiBubble.className = "message-bubble assistant";
    aiBubble.id = `ai-bubble-${turnId}`;
    aiBubble.innerHTML = `
        <div class="bubble-header">
            <span class="bubble-role">${aiRoleLabel}</span>
            <div class="bubble-meta-header">
                <span class="bubble-time ai-time">${timeStr}</span>
                <span id="ai-latency-${turnId}" class="latency-pill hidden">⚡ <span class="ttfa-val">--</span> ms</span>
            </div>
        </div>
        <div id="ai-text-${turnId}" class="bubble-text-en"></div>
        <div id="ai-tr-${turnId}" class="bubble-text-es hidden"><span>🇪🇸</span> <span class="ai-translation-content"></span></div>
        <div id="ai-meta-${turnId}" class="bubble-meta ai-meta hidden">
            <span>⏱️ Respuesta en: <span class="total-time-val">--</span> s</span>
        </div>
    `;
    chatMessages.appendChild(aiBubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateUserTranslation(spanishText, turnId) {
    if (!spanishText) return;
    const el = document.getElementById(`user-tr-${turnId}`);
    if (el) {
        el.innerText = spanishText;
        el.classList.remove("translation-placeholder");
    }
}

function appendAiChunk(delta, turnId) {
    const textEl = document.getElementById(`ai-text-${turnId}`);
    if (textEl) {
        textEl.innerText += delta;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function updateAiTranslation(spanishText, turnId) {
    if (!spanishText) return;
    const container = document.getElementById(`ai-tr-${turnId}`);
    if (container) {
        const content = container.querySelector(".ai-translation-content");
        if (content) content.innerText = spanishText;
        container.classList.remove("hidden");
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function showCoachingTip(tip) {
    if (!tip) return;
    const box = document.createElement("div");
    box.className = "tip-box";
    box.innerHTML = `<strong>💡 Observación:</strong> ${escapeHtml(tip)}`;

    if (coachingContent.querySelector(".empty-tip")) {
        coachingContent.innerHTML = "";
    }
    coachingContent.prepend(box);
}

function addToVocabulary(sentence) {
    if (vocabularyList.querySelector(".empty-tip")) {
        vocabularyList.innerHTML = "";
    }
    const item = document.createElement("div");
    item.style.padding = "6px 0";
    item.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
    item.innerText = `• "${sentence}"`;
    vocabularyList.prepend(item);
}

function enqueueAudio(base64Wav) {
    const audioObj = new Audio("data:audio/wav;base64," + base64Wav);
    audioObj.preload = "auto";
    audioQueue.push(audioObj);
    if (!isAudioPlaying) {
        playNextAudioChunk();
    }
}

function playNextAudioChunk() {
    if (audioQueue.length === 0) {
        isAudioPlaying = false;
        currentAudioElement = null;
        interruptBtn.classList.add("hidden");
        if (isCallMode) {
            setOrbState("listening", "📞 Te escucho...");
        } else {
            setOrbState("idle", "Listo para conversar");
        }
        return;
    }

    isAudioPlaying = true;
    interruptBtn.classList.remove("hidden");
    setOrbState("speaking", "Hablando...");

    currentAudioElement = audioQueue.shift();

    currentAudioElement.onended = () => {
        playNextAudioChunk();
    };

    currentAudioElement.onerror = (e) => {
        console.error("Error en audio:", e);
        playNextAudioChunk();
    };

    currentAudioElement.play().catch(e => {
        console.warn("Autoplay:", e);
        playNextAudioChunk();
    });
}

function stopAudioPlayback() {
    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
    }
    audioQueue.length = 0;
    isAudioPlaying = false;
    interruptBtn.classList.add("hidden");
}

interruptBtn.addEventListener("click", () => {
    stopAudioPlayback();
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "interrupt" }));
    }
});

// ==========================================
// VISUALIZADOR Y ENCODER WAV MODULARES
// Delegados a static/js/visualizer.js y static/js/wav-encoder.js
// ==========================================

function sendWavBuffer(samples, messageType = "audio_final", turnId = null) {
    if (samples.length < 4000) return;
    const wavBlob = encodeWAV(samples, 16000);
    const reader = new FileReader();
    reader.readAsDataURL(wavBlob);
    reader.onloadend = () => {
        const base64Wav = reader.result.split(",")[1];
        if (socket && socket.readyState === WebSocket.OPEN) {
            const payload = {
                type: messageType,
                audio: base64Wav
            };
            if (messageType === "audio_final") {
                turnStartTime = Date.now();
                payload.turn_id = turnId || ("turn-" + turnStartTime);
            }
            socket.send(JSON.stringify(payload));
        }
    };
}

// ==========================================
// SELECCIÓN DE DISPOSITIVO DE AUDIO
// ==========================================

async function populateMicrophones() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = devices.filter(d => d.kind === "audioinput");

        if (micSelect && audioInputs.length > 0) {
            micSelect.innerHTML = "";
            let preferredIndex = 0;

            audioInputs.forEach((device, index) => {
                const opt = document.createElement("option");
                opt.value = device.deviceId;
                opt.innerText = device.label || `Micrófono ${index + 1}`;

                const labelLow = (device.label || "").toLowerCase();
                if (labelLow.includes("sz01") || labelLow.includes("headset") || labelLow.includes("micrófono")) {
                    if (!labelLow.includes("cable") && !labelLow.includes("virtual")) {
                        preferredIndex = index;
                    }
                }
                micSelect.appendChild(opt);
            });

            micSelect.selectedIndex = preferredIndex;
        }
    } catch (e) {
        console.warn("Dispositivos:", e);
    }
}

// ==========================================
// STREAMING DE AUDIO + VAD + PARCIALES EN VIVO
// ==========================================

async function setupAudioStream() {
    if (mediaStream && audioContext) return true;

    // 1. Verificación de Secure Context para dispositivos móviles (iOS Safari / Android Chrome)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
        const currentProto = window.location.protocol;

        if (currentProto === "http:" && !isLocal) {
            const httpsUrl = `https://${window.location.hostname}:8000`;
            showSecureContextModal(httpsUrl);
            return false;
        }

        showSystemNotification("Tu navegador no soporta o bloquea la captura de audio en esta conexión.");
        return false;
    }

    try {
        const selectedDeviceId = micSelect ? micSelect.value : "";
        const audioConstraints = {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
        };

        if (selectedDeviceId) {
            audioConstraints.deviceId = { exact: selectedDeviceId };
        }

        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
        populateMicrophones();

        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);

        const micAnalyser = audioContext.createAnalyser();
        micAnalyser.fftSize = 256;
        source.connect(micAnalyser);
        if (window.AudioVisualizer) {
            window.AudioVisualizer.setAnalyser(micAnalyser);
        }

        const gainNode = audioContext.createGain();
        gainNode.gain.value = 1.0; // Ganancia 1:1 natural (evita amplificar respiraciones y ruidos de fondo)

        scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

        scriptProcessor.onaudioprocess = (e) => {
            const inputData = e.inputBuffer.getChannelData(0);
            let sum = 0;
            for (let i = 0; i < inputData.length; i++) {
                const s = inputData[i];
                sum += s * s;
            }
            const rms = Math.sqrt(sum / inputData.length);
            if (rms > peakRmsObserved) peakRmsObserved = rms;

            const pct = Math.min(100, Math.round(rms * 400));
            if (meterBarFill) {
                meterBarFill.style.width = pct + "%";
                meterBarFill.style.background = rms > VAD_THRESHOLD ? "#10b981" : "#3b82f6";
            }

            // --- LÓGICA DE MODO LLAMADA CONTINUO + TRANSCRIPCIÓN EN VIVO ---
            if (isCallMode) {
                const now = Date.now();
                const hasSpokenTooLong = isUserSpeakingInCall && (now - speechStartTime > MAX_SPEECH_DURATION_MS);

                if (rms > VAD_THRESHOLD && !hasSpokenTooLong) {
                    // BARGE-IN INMEDIATO: Si la IA está hablando, cortarla al instante
                    if (isAudioPlaying) {
                        stopAudioPlayback();
                        if (socket && socket.readyState === WebSocket.OPEN) {
                            socket.send(JSON.stringify({ type: "interrupt" }));
                        }
                    }

                    if (!isUserSpeakingInCall) {
                        isUserSpeakingInCall = true;
                        speechStartTime = now;
                        callAudioBuffer = [];
                        lastPartialSendTime = now;
                        setOrbState("listening", "📞 Te escucho...");
                    }

                    if (callSilenceTimer) {
                        clearTimeout(callSilenceTimer);
                        callSilenceTimer = null;
                    }

                    for (let i = 0; i < inputData.length; i++) {
                        callAudioBuffer.push(inputData[i]);
                    }

                    // Enviar transcripción parcial continua cada 450ms mientras habla
                    if (!isPartialSttPending && now - lastPartialSendTime > 450 && callAudioBuffer.length >= 6400) {
                        lastPartialSendTime = now;
                        isPartialSttPending = true;
                        sendWavBuffer(callAudioBuffer, "audio_partial");
                    }
                } else if (isUserSpeakingInCall) {
                    // Pausa / silencio temporal o límite de tiempo alcanzado
                    for (let i = 0; i < inputData.length; i++) {
                        callAudioBuffer.push(inputData[i]);
                    }

                    const timeoutToUse = hasSpokenTooLong ? 50 : SILENCE_TIMEOUT_MS;

                    if (!callSilenceTimer) {
                        callSilenceTimer = setTimeout(() => {
                            isUserSpeakingInCall = false;
                            isPartialSttPending = false;
                            callSilenceTimer = null;
                            speechStartTime = 0;
                            setOrbState("thinking", "Pensando respuesta...");
                            const turnId = "turn-" + Date.now();
                            sendWavBuffer(callAudioBuffer, "audio_final", turnId);
                            callAudioBuffer = [];
                        }, timeoutToUse);
                    }
                }
            } else if (isRecording) {
                // Modo manual
                for (let i = 0; i < inputData.length; i++) {
                    audioSamples.push(inputData[i]);
                }
            }
        };

        source.connect(gainNode);
        gainNode.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination);
        return true;
    } catch (err) {
        showSystemNotification("Error con el micrófono: " + err.message);
        return false;
    }
}

// ==========================================
// MODO LLAMADA FLUIDA (MANOS LIBRES)
// ==========================================

async function toggleCallMode() {
    if (!isCallMode) {
        const ok = await setupAudioStream();
        if (!ok) return;

        isCallMode = true;
        callModeBtn.classList.add("active");
        callBtnText.innerText = "🔴 En Llamada (Habla libremente - Clic para Colgar)";
        if (micMeterContainer) micMeterContainer.classList.remove("hidden");
        setOrbState("listening", "📞 Llamada activa: habla cuando quieras");
    } else {
        isCallMode = false;
        isUserSpeakingInCall = false;
        if (callSilenceTimer) {
            clearTimeout(callSilenceTimer);
            callSilenceTimer = null;
        }
        stopAudioPlayback();
        callModeBtn.classList.remove("active");
        callBtnText.innerText = "📞 Iniciar Modo Llamada (Manos Libres)";
        if (micMeterContainer) micMeterContainer.classList.add("hidden");
        setOrbState("idle", "Listo para conversar");
    }
}

if (callModeBtn) {
    callModeBtn.addEventListener("click", toggleCallMode);
}

// ==========================================
// MODO MANUAL (PULSAR PARA HABLAR)
// ==========================================

async function startRecording() {
    if (isCallMode) return;
    if (isAudioPlaying) {
        stopAudioPlayback();
        socket.send(JSON.stringify({ type: "interrupt" }));
    }

    const ok = await setupAudioStream();
    if (!ok) return;

    audioSamples = [];
    peakRmsObserved = 0;
    isRecording = true;
    micBtn.classList.add("recording");
    micBtnLabel.innerText = "Toca para ENVIAR";
    if (micMeterContainer) micMeterContainer.classList.remove("hidden");
    setOrbState("listening", "Escuchando... habla con naturalidad");
}

function stopRecording() {
    if (isCallMode || !isRecording) return;
    isRecording = false;

    micBtn.classList.remove("recording");
    micBtnLabel.innerText = "Pulsar para hablar";
    if (micMeterContainer) micMeterContainer.classList.add("hidden");
    if (meterBarFill) meterBarFill.style.width = "0%";
    setOrbState("thinking", "Transcribiendo tu voz...");

    if (audioSamples.length < 6400) {
        showSystemNotification("Grabación muy corta (< 0.4s). Habla al menos 1 o 2 segundos.");
        setOrbState("idle", "Listo para conversar");
        return;
    }

    const turnId = "turn-" + Date.now();
    sendWavBuffer(audioSamples, "audio_final", turnId);
}

micBtn.addEventListener("click", () => {
    if (isCallMode) {
        alert("El Modo Llamada está activo (manos libres). Solo habla con naturalidad.");
        return;
    }
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
});

function sendTextMessage() {
    const text = textInput.value.trim();
    if (!text) return;

    if (isAudioPlaying) {
        stopAudioPlayback();
        socket.send(JSON.stringify({ type: "interrupt" }));
    }

    if (socket && socket.readyState === WebSocket.OPEN) {
        turnStartTime = Date.now();
        const turnId = "turn-" + turnStartTime;
        socket.send(JSON.stringify({
            type: "text",
            turn_id: turnId,
            text: text
        }));
    }

    textInput.value = "";
}

sendBtn.addEventListener("click", sendTextMessage);
textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        sendTextMessage();
    }
});

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}

window.addEventListener("DOMContentLoaded", async () => {
    if (window.I18nManager) {
        await window.I18nManager.init();
    }
    connectWebSocket();
    populateMicrophones();

    function updateThresholdMarker() {
        if (meterThresholdLine) {
            const threshPct = Math.min(95, Math.max(5, Math.round(VAD_THRESHOLD * 400)));
            meterThresholdLine.style.left = threshPct + "%";
        }
    }

    if (vadSelect) {
        vadSelect.value = VAD_THRESHOLD.toString();
        updateThresholdMarker();
        vadSelect.addEventListener("change", () => {
            VAD_THRESHOLD = parseFloat(vadSelect.value);
            updateThresholdMarker();
            console.log("VAD Threshold ajustado a:", VAD_THRESHOLD);
        });
    }

    // Listener selector de voz IA
    if (voiceSelect) {
        voiceSelect.addEventListener("change", () => {
            const chosenVoice = voiceSelect.value;
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: "set_voice",
                    voice: chosenVoice
                }));
            }
        });
    }

    // Listener botón Modo Susurro (Whisper Mode)
    if (whisperBtn) {
        whisperBtn.addEventListener("click", () => {
            const nextState = !isWhisperMode;
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: "set_whisper_mode",
                    enabled: nextState
                }));
            } else {
                isWhisperMode = nextState;
                whisperBtn.classList.toggle("active", isWhisperMode);
                whisperBtn.setAttribute("aria-pressed", isWhisperMode ? "true" : "false");
                if (whisperBtnLabel && window.I18nManager) {
                    whisperBtnLabel.innerText = isWhisperMode ? 
                        (I18nManager.t("whisper_on") || "Activado") : 
                        (I18nManager.t("whisper_off") || "Desactivado");
                }
            }
        });
    }

    // Selector de modo de idioma
    document.querySelectorAll(".lang-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentLanguageMode = btn.dataset.mode;

            // Sincronizar traducción completa de la interfaz de usuario (i18n)
            if (window.I18nManager) {
                if (currentLanguageMode === "es") {
                    window.I18nManager.setLanguage("es", false);
                } else if (currentLanguageMode === "en") {
                    window.I18nManager.setLanguage("en", false);
                } else {
                    window.I18nManager.applyLanguage(window.I18nManager.currentLang);
                }
            }

            // Auto-seleccionar la mejor voz para el modo (preservando mezclas híbridas si el usuario las eligió)
            if (voiceSelect) {
                const isBlend = voiceSelect.value.startsWith("blend");
                if (!isBlend) {
                    if (currentLanguageMode === "es" && !voiceSelect.value.startsWith("e")) {
                        voiceSelect.value = "ef_dora";
                    } else if (currentLanguageMode === "en" && !voiceSelect.value.startsWith("a")) {
                        voiceSelect.value = "af_sarah";
                    }
                }
            }

            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: "set_mode",
                    mode: currentLanguageMode
                }));
                if (voiceSelect) {
                    socket.send(JSON.stringify({
                        type: "set_voice",
                        voice: voiceSelect.value
                    }));
                }
            }

            if (currentLanguageMode === "es") {
                setOrbState("idle", "🇪🇸 Asistente en español listo (Voz nativa)");
                if (textInput) textInput.placeholder = "Escribe un mensaje en español...";
            } else if (currentLanguageMode === "en") {
                setOrbState("idle", "🇺🇸 English tutor ready");
                if (textInput) textInput.placeholder = "Write a message in English...";
            } else {
                setOrbState("idle", "🌐 Modo bilingüe listo");
                if (textInput) textInput.placeholder = "Escribe o habla en inglés o español...";
            }
        });
    });

    // Manejo de ejecución de herramientas directas (Tool Calling)
    function handleToolExecuted(data) {
        const { turn_id, tool, display_text } = data;
        const textEl = document.getElementById(`ai-text-${turn_id}`);
        if (textEl) {
            textEl.innerHTML = `<div class="tool-badge">🔧 Herramienta: ${escapeHtml(tool)}</div><div>${escapeHtml(display_text)}</div>`;
        }
        if (tool === "save_voice_note" || tool === "list_voice_notes") {
            loadPersistentNotes();
        }
        if (tool === "list_vocabulary") {
            loadPersistentVocabulary();
        }
    }

    // Cargar notas persistentes de voz desde SQLite
    async function loadPersistentNotes() {
        const notesList = document.getElementById("notes-list");
        if (!notesList) return;
        try {
            const res = await fetch("/api/notes");
            if (res.ok) {
                const notes = await res.json();
                if (notes && notes.length > 0) {
                    notesList.innerHTML = "";
                    notes.forEach(n => {
                        const div = document.createElement("div");
                        div.className = "note-item";
                        div.innerHTML = `<strong>${escapeHtml(n.title)}</strong><span>${escapeHtml(n.content)}</span>`;
                        notesList.appendChild(div);
                    });
                } else {
                    notesList.innerHTML = '<div class="empty-tip">No hay notas guardadas todavía. Di: "Toma nota de..."</div>';
                }
            }
        } catch (e) {
            console.warn("No se pudo cargar notas persistentes:", e);
        }
    }

    // Cargar historial reciente de conversación desde SQLite
    async function loadPersistentHistory() {
        try {
            const res = await fetch("/api/history");
            if (res.ok) {
                const msgs = await res.json();
                if (msgs && msgs.length > 0 && chatMessages) {
                    const welcomeCard = chatMessages.querySelector(".welcome-card");
                    if (welcomeCard) welcomeCard.remove();
                    
                    msgs.forEach(m => {
                        const bubble = document.createElement("div");
                        bubble.className = `message-bubble ${m.role}`;
                        const timeStr = m.created_at ? (m.created_at.includes(" ") ? m.created_at.split(" ")[1] : m.created_at) : "";
                        const roleLabel = m.role === "user" ? "👤 Tú (Historial)" : "🤖 Asistente (Historial)";
                        bubble.innerHTML = `
                            <div class="bubble-header">
                                <span class="bubble-role">${roleLabel}</span>
                                <span class="bubble-time">${timeStr}</span>
                            </div>
                            <div class="bubble-text-en">${escapeHtml(m.content)}</div>
                            ${m.translation ? `<div class="bubble-text-es"><span>🇪🇸</span> ${escapeHtml(m.translation)}</div>` : ""}
                        `;
                        chatMessages.appendChild(bubble);
                    });
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            }
        } catch (e) {
            console.warn("No se pudo cargar historial:", e);
        }
    }

    // Cargar vocabulario persistente desde SQLite
    async function loadPersistentVocabulary() {
        try {
            const res = await fetch("/api/vocabulary");
            if (res.ok) {
                const items = await res.json();
                if (items && items.length > 0 && vocabularyList) {
                    vocabularyList.innerHTML = "";
                    items.forEach(v => {
                        const div = document.createElement("div");
                        div.className = "vocab-item";
                        div.innerHTML = `<strong>• ${escapeHtml(v.phrase)}</strong>${v.tip ? `<br><small style="color: #93c5fd;">💡 ${escapeHtml(v.tip)}</small>` : ''}`;
                        div.style.padding = "6px 0";
                        div.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
                        vocabularyList.appendChild(div);
                    });
                }
            }
        } catch (e) {
            console.warn("No se pudo cargar vocabulario persistente:", e);
        }
    }

    // Cargar perfil del usuario desde SQLite
    async function loadUserProfile() {
        try {
            const res = await fetch("/api/profile");
            if (res.ok) {
                const profile = await res.json();
                const badge = document.getElementById("user-profile-badge");
                if (badge && profile.name) {
                    badge.innerText = `👤 ${profile.name}`;
                }
            }
        } catch (e) {
            console.warn("No se pudo cargar perfil de usuario:", e);
        }
    }

    // Listener del selector global de idioma UI (8 Idiomas)
    const uiLangSelect = document.getElementById("ui-lang-select");
    if (uiLangSelect) {
        uiLangSelect.value = currentUiLang;
        uiLangSelect.addEventListener("change", (e) => {
            setUiLanguage(e.target.value);
        });
    }

    // Exportar sesión completa de voz a Markdown
    function exportSessionToMarkdown() {
        const bubbles = document.querySelectorAll(".message-bubble");
        if (!bubbles || bubbles.length === 0) {
            alert(currentUiLang === "es" ? "No hay intervenciones en la sesión para exportar." : "No messages in session to export.");
            return;
        }
        let md = `# 🎙️ Sesión de Asistente de Voz Local (Exportada)\n\n`;
        md += `* **Usuario:** Cristian Arboleda\n`;
        md += `* **Fecha:** ${new Date().toLocaleString()}\n`;
        md += `* **Idioma UI:** ${currentUiLang.toUpperCase()}\n\n---\n\n`;

        bubbles.forEach(b => {
            const role = b.classList.contains("user") ? "👤 Usuario" : "🤖 Asistente";
            const timeEl = b.querySelector(".bubble-time");
            const time = timeEl ? ` [${timeEl.innerText}]` : "";
            const textEl = b.querySelector(".bubble-text-en");
            const text = textEl ? textEl.innerText.trim() : "";
            const trEl = b.querySelector(".bubble-text-es");
            const tr = trEl ? trEl.innerText.trim() : "";

            md += `### ${role}${time}\n${text}\n`;
            if (tr) md += `> ${tr}\n`;
            md += `\n`;
        });

        const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `voice-session-${new Date().toISOString().slice(0, 10)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    const exportHistoryBtn = document.getElementById("export-history-btn");
    if (exportHistoryBtn) {
        exportHistoryBtn.addEventListener("click", exportSessionToMarkdown);
    }

    if (personalitySelect) {
        personalitySelect.addEventListener("change", (e) => {
            const pers = e.target.value;
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: "set_personality",
                    personality: pers
                }));
            }
        });
    }

    // Inicializar visualizador 60 FPS
    if (window.AudioVisualizer) {
        window.AudioVisualizer.init();
    }
    loadUserProfile();
    loadPersistentVocabulary();
    loadPersistentNotes();
    loadPersistentHistory();

    const clearHistoryBtn = document.getElementById("clear-history-btn");
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener("click", async () => {
            const confirmMsg = window.I18nManager ? window.I18nManager.t("clear_confirm") : "¿Deseas vaciar la base de datos de conversaciones, notas y vocabulario guardado?";
            if (confirm(confirmMsg)) {
                try {
                    await fetch("/api/history", { method: "DELETE" });
                    const doneMsg = window.I18nManager ? window.I18nManager.t("clear_done") : "Historial y vocabulario limpiados.";
                    if (vocabularyList) {
                        vocabularyList.innerHTML = `<div class="empty-tip">${doneMsg}</div>`;
                    }
                    const notesList = document.getElementById("notes-list");
                    if (notesList) {
                        notesList.innerHTML = '<div class="empty-tip">Di "Toma nota de..." para guardar notas por voz.</div>';
                    }
                    if (chatMessages) {
                        chatMessages.innerHTML = '';
                    }
                } catch (err) {
                    console.error("Error al limpiar historial:", err);
                }
            }
        });
    }
});
