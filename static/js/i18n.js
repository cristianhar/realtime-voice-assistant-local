// static/js/i18n.js - Gestor Modular de Internacionalización (i18n)
const DEFAULT_FALLBACK_LOCALES = {
    "es": {
        "mode_en": "🇺🇸 Practicar Inglés",
        "mode_es": "🇪🇸 Español",
        "mode_auto": "🌐 Bilingüe / Auto",
        "connecting": "Conectando...",
        "connected": "Conectado (Local)",
        "disconnected": "Desconectado. Reintentando...",
        "orb_ready": "Listo para conversar",
        "orb_listening": "📞 Te escucho...",
        "orb_speaking": "Hablando...",
        "orb_thinking": "Pensando respuesta...",
        "welcome_title": "👋 ¡Bienvenido a tu Sala de Voz con IA Local!",
        "welcome_desc": "Habla libremente con naturalidad. Verás la transcripción en vivo palabra por palabra, traducciones, notas guardadas y feedback en tiempo real.",
        "tip_no_limits": "💡 Sin límites de tiempo",
        "tip_offline": "⚡ 100% Local y privado",
        "tip_memory": "🎯 Memoria RAG y herramientas",
        "input_placeholder_en": "Escribe un mensaje en inglés...",
        "input_placeholder_es": "Escribe un mensaje en español...",
        "input_placeholder_auto": "Escribe o habla en inglés o español...",
        "call_btn_start": "Iniciar Modo Llamada (Manos Libres)",
        "call_btn_stop": "Finalizar Modo Llamada",
        "label_mic": "🎤 Mic:",
        "label_voice": "🗣️ Voz IA:",
        "label_vad": "🎚️ Filtro VAD:",
        "label_personality": "🎭 Personalidad:",
        "label_speed": "⏩ Velocidad:",
        "label_whisper": "🌙 Susurro:",
        "whisper_off": "Desactivado",
        "whisper_on": "Activado",
        "pers_coach": "🎓 Tutor de Idiomas",
        "pers_friendly": "🤗 Amigo Casual",
        "pers_tech": "💻 Senior Tech Lead",
        "pers_executive": "👔 Mentor Ejecutivo",
        "pers_interviewer": "💼 Entrevistador Técnico & IELTS",
        "vad_low": "Baja (Filtra respiración fuerte y ventilador)",
        "vad_med": "Media (Recomendada)",
        "vad_high": "Alta (Habla muy suave)",
        "mic_btn_speak": "Pulsar para hablar",
        "mic_btn_listening": "Escuchando...",
        "interrupt_btn": "⏹ Interrumpir",
        "meter_label": "Nivel de voz:",
        "panel_coaching": "🎯 Tutor Feedback & Grammar",
        "panel_coaching_empty": "Habla en inglés para recibir observaciones gramaticales y sugerencias de vocabulario en tiempo real.",
        "panel_vocab": "📝 Vocabulario & Frases",
        "panel_vocab_empty": "Aquí se guardarán las oraciones clave de la sesión.",
        "panel_notes": "📌 Notas Rápidas por Voz",
        "panel_notes_empty": "Di \"Toma nota de...\" o \"Recuérdame...\" para guardar notas por voz.",
        "panel_metrics": "⚡ Rendimiento en Tiempo Real",
        "metric_time": "Hora último mensaje:",
        "metric_stt": "Whisper STT (Voz):",
        "metric_ttfa": "Latencia 1er Audio (TTFA):",
        "metric_total": "Tiempo Total Respuesta:",
        "metric_vram": "VRAM Utilizada:",
        "tool_badge": "🔧 Herramienta: ",
        "clear_confirm": "¿Deseas vaciar la base de datos de conversaciones, notas y vocabulario guardado?",
        "clear_done": "Historial, notas y vocabulario limpiados."
    },
    "en": {
        "mode_en": "🇺🇸 Practice English",
        "mode_es": "🇪🇸 Spanish Assistant",
        "mode_auto": "🌐 Bilingual / Auto",
        "connecting": "Connecting...",
        "connected": "Connected (Local)",
        "disconnected": "Disconnected. Retrying...",
        "orb_ready": "Ready to converse",
        "orb_listening": "📞 Listening to you...",
        "orb_speaking": "Speaking...",
        "orb_thinking": "Thinking response...",
        "welcome_title": "👋 Welcome to your Local AI Voice Room!",
        "welcome_desc": "Speak naturally and freely. You will see live word-by-word transcription, translations, saved voice notes, and real-time coaching feedback.",
        "tip_no_limits": "💡 No time limits",
        "tip_offline": "⚡ 100% Local & private",
        "tip_memory": "🎯 RAG Memory & Voice Tools",
        "input_placeholder_en": "Type a message in English...",
        "input_placeholder_es": "Type a message in Spanish...",
        "input_placeholder_auto": "Type or speak in English or Spanish...",
        "call_btn_start": "Start Hands-Free Call Mode",
        "call_btn_stop": "End Call Mode",
        "label_mic": "🎤 Mic:",
        "label_voice": "🗣️ AI Voice:",
        "label_vad": "🎚️ VAD Sensitivity:",
        "label_personality": "🎭 Personality:",
        "label_speed": "⏩ Speed:",
        "label_whisper": "🌙 Whisper:",
        "whisper_off": "Off",
        "whisper_on": "Active",
        "pers_coach": "🎓 Language Coach",
        "pers_friendly": "🤗 Casual Friend",
        "pers_tech": "💻 Senior Tech Lead",
        "pers_executive": "👔 Executive Mentor",
        "pers_interviewer": "💼 Tech & IELTS Interviewer",
        "vad_low": "Low (Filters strong breaths and fan)",
        "vad_med": "Medium (Recommended)",
        "vad_high": "High (Detects soft whisper)",
        "mic_btn_speak": "Tap to speak",
        "mic_btn_listening": "Listening...",
        "interrupt_btn": "⏹ Interrupt",
        "meter_label": "Voice level:",
        "panel_coaching": "🎯 Grammar & Coaching Feedback",
        "panel_coaching_empty": "Speak in English to receive grammar feedback and vocabulary suggestions in real time.",
        "panel_vocab": "📝 Vocabulary & Phrases",
        "panel_vocab_empty": "Key phrases from your session will appear here.",
        "panel_notes": "📌 Quick Voice Notes",
        "panel_notes_empty": "Say \"Take a note...\" or \"Remind me...\" to save voice notes.",
        "panel_metrics": "⚡ Real-Time Latency",
        "metric_time": "Last Message Time:",
        "metric_stt": "Whisper STT (Speech):",
        "metric_ttfa": "First Audio Latency (TTFA):",
        "metric_total": "Total Response Time:",
        "metric_vram": "VRAM Usage:",
        "tool_badge": "🔧 Tool: ",
        "clear_confirm": "Do you want to clear conversation history, saved notes and vocabulary?",
        "clear_done": "History, notes and vocabulary cleared."
    }
};

const I18nManager = {
    locales: DEFAULT_FALLBACK_LOCALES,
    currentLang: localStorage.getItem("ui_lang") || "es",
    isLoaded: false,

    async init() {
        try {
            const res = await fetch("/static/locales.json");
            if (res.ok) {
                const data = await res.json();
                this.locales = { ...DEFAULT_FALLBACK_LOCALES, ...data };
                this.isLoaded = true;
            }
        } catch (e) {
            console.warn("No se pudo cargar /static/locales.json (usando respaldo en memoria):", e);
        }

        const sel = document.getElementById("ui-lang-select");
        if (sel) {
            sel.value = this.currentLang;
            sel.addEventListener("change", (e) => {
                this.setLanguage(e.target.value, true);
            });
        }

        this.applyLanguage(this.currentLang);
    },

    t(key) {
        const langDict = this.locales[this.currentLang] || this.locales["es"] || {};
        return langDict[key] || key;
    },

    setLanguage(lang, syncMode = true) {
        this.currentLang = lang;
        localStorage.setItem("ui_lang", lang);
        this.applyLanguage(lang);

        if (syncMode) {
            if (lang === "es") {
                const btnEs = document.getElementById("btn-mode-es");
                if (btnEs && !btnEs.classList.contains("active")) {
                    btnEs.click();
                }
            } else if (lang === "en") {
                const btnEn = document.getElementById("btn-mode-en");
                if (btnEn && !btnEn.classList.contains("active")) {
                    btnEn.click();
                }
            }
        }
    },

    applyLanguage(lang) {
        const t = this.locales[lang] || this.locales["es"];
        if (!t) return;

        const sel = document.getElementById("ui-lang-select");
        if (sel && sel.value !== lang) sel.value = lang;

        const mEn = document.getElementById("btn-mode-en");
        const mEs = document.getElementById("btn-mode-es");
        const mAuto = document.getElementById("btn-mode-auto");
        if (mEn) mEn.innerText = t.mode_en;
        if (mEs) mEs.innerText = t.mode_es;
        if (mAuto) mAuto.innerText = t.mode_auto;

        const wTitle = document.getElementById("welcome-title");
        const wDesc = document.getElementById("welcome-desc");
        const tip1 = document.getElementById("tip-1");
        const tip2 = document.getElementById("tip-2");
        const tip3 = document.getElementById("tip-3");
        if (wTitle) wTitle.innerText = t.welcome_title;
        if (wDesc) wDesc.innerText = t.welcome_desc;
        if (tip1) tip1.innerText = t.tip_no_limits;
        if (tip2) tip2.innerText = t.tip_offline;
        if (tip3) tip3.innerText = t.tip_memory;

        const textInput = document.getElementById("text-input");
        if (textInput) {
            const mode = window.currentLanguageMode || "en";
            if (mode === "es") textInput.placeholder = t.input_placeholder_es;
            else if (mode === "en") textInput.placeholder = t.input_placeholder_en;
            else textInput.placeholder = t.input_placeholder_auto;
        }

        const callBtnText = document.getElementById("call-btn-text");
        const callModeBtn = document.getElementById("call-mode-btn");
        if (callBtnText) {
            callBtnText.innerText = window.isCallMode ? t.call_btn_stop : t.call_btn_start;
        }
        if (callModeBtn) {
            callModeBtn.title = window.isCallMode ? t.call_btn_stop : (t.call_btn_start || "Conversación Ininterrumpida");
        }

        const micBtnLabel = document.getElementById("mic-btn-label");
        const micBtn = document.getElementById("mic-btn");
        if (micBtnLabel) {
            micBtnLabel.innerText = window.isRecording ? t.mic_btn_listening : t.mic_btn_speak;
        }
        if (micBtn) {
            micBtn.title = window.isRecording ? t.mic_btn_listening : (t.mic_btn_speak || "Pulsar para hablar");
        }

        const interruptBtn = document.getElementById("interrupt-btn");
        if (interruptBtn) {
            interruptBtn.title = t.interrupt_btn || "Interrumpir a la IA";
            const srText = interruptBtn.querySelector(".sr-only");
            if (srText) srText.innerText = t.interrupt_btn;
            else interruptBtn.innerText = t.interrupt_btn;
        }

        const lMic = document.getElementById("label-mic");
        const lVoice = document.getElementById("label-voice");
        const lVad = document.getElementById("label-vad");
        const lPers = document.getElementById("label-personality");
        const lSpeed = document.getElementById("label-speed");
        const lWhisper = document.getElementById("label-whisper");
        const whisperBtnLabel = document.getElementById("whisper-btn-label");
        if (lMic) lMic.innerText = t.label_mic;
        if (lVoice) lVoice.innerText = t.label_voice;
        if (lVad) lVad.innerText = t.label_vad;
        if (lPers && t.label_personality) lPers.innerText = t.label_personality;
        if (lSpeed && t.label_speed) lSpeed.innerText = t.label_speed;
        if (lWhisper && t.label_whisper) lWhisper.innerText = t.label_whisper;
        if (whisperBtnLabel) {
            whisperBtnLabel.innerText = window.isWhisperMode ? (t.whisper_on || "Activado") : (t.whisper_off || "Desactivado");
        }

        const personalitySelect = document.getElementById("personality-select");
        if (personalitySelect && t.pers_coach) {
            const optCoach = personalitySelect.querySelector('option[value="coach"]');
            const optFriend = personalitySelect.querySelector('option[value="friendly"]');
            const optTech = personalitySelect.querySelector('option[value="tech"]');
            const optExec = personalitySelect.querySelector('option[value="executive"]');
            const optInterviewer = personalitySelect.querySelector('option[value="interviewer"]');
            if (optCoach) optCoach.innerText = t.pers_coach;
            if (optFriend) optFriend.innerText = t.pers_friendly;
            if (optTech) optTech.innerText = t.pers_tech;
            if (optExec) optExec.innerText = t.pers_executive;
            if (optInterviewer && t.pers_interviewer) optInterviewer.innerText = t.pers_interviewer;
        }

        const optLow = document.getElementById("opt-vad-low");
        const optMed = document.getElementById("opt-vad-med");
        const optHigh = document.getElementById("opt-vad-high");
        if (optLow) optLow.innerText = t.vad_low;
        if (optMed) optMed.innerText = t.vad_med;
        if (optHigh) optHigh.innerText = t.vad_high;

        const mLabel = document.getElementById("meter-label-text");
        if (mLabel) mLabel.innerText = t.meter_label;

        const pCoaching = document.getElementById("panel-title-coaching");
        const pVocab = document.getElementById("panel-title-vocab");
        const pNotes = document.getElementById("panel-title-notes");
        const pMetrics = document.getElementById("panel-title-metrics");
        if (pCoaching) pCoaching.innerText = t.panel_coaching;
        if (pVocab) pVocab.innerText = t.panel_vocab;
        if (pNotes) pNotes.innerText = t.panel_notes;
        if (pMetrics) pMetrics.innerText = t.panel_metrics;

        const emptyCoaching = document.getElementById("empty-tip-coaching");
        const emptyVocab = document.getElementById("empty-tip-vocab");
        const emptyNotes = document.getElementById("empty-tip-notes");
        if (emptyCoaching) emptyCoaching.innerText = t.panel_coaching_empty;
        if (emptyVocab) emptyVocab.innerText = t.panel_vocab_empty;
        if (emptyNotes) emptyNotes.innerText = t.panel_notes_empty;

        const mTime = document.getElementById("metric-label-time");
        const mStt = document.getElementById("metric-label-stt");
        const mTts = document.getElementById("metric-label-tts");
        const mTotal = document.getElementById("metric-label-total");
        const mVram = document.getElementById("metric-label-vram");
        if (mTime) mTime.innerText = t.metric_time;
        if (mStt) mStt.innerText = t.metric_stt;
        if (mTts) mTts.innerText = t.metric_ttfa;
        if (mTotal) mTotal.innerText = t.metric_total;
        if (mVram) mVram.innerText = t.metric_vram;

        const orbLabel = document.getElementById("orb-label");
        if (orbLabel && !window.isAudioPlaying && !window.isRecording) {
            orbLabel.innerText = t.orb_ready;
        }

        const btnHistoryText = document.getElementById("btn-history-text");
        if (btnHistoryText) btnHistoryText.innerText = t.chats || "Chats";
        const drawerHistoryTitle = document.getElementById("drawer-history-title");
        if (drawerHistoryTitle) drawerHistoryTitle.innerText = t.history_title || "Historial de Conversaciones";
        const btnNewChatText = document.getElementById("btn-new-chat-text");
        if (btnNewChatText) btnNewChatText.innerText = t.new_chat || "Nueva Conversación";
        const historySearchInput = document.getElementById("history-search-input");
        if (historySearchInput) historySearchInput.placeholder = t.search_chats || "🔍 Buscar conversaciones...";
    }
};

// Auto-inicializar en cuanto el DOM esté listo
if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => I18nManager.init());
    } else {
        I18nManager.init();
    }
}

window.I18nManager = I18nManager;

