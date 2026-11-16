// static/js/i18n.js - Gestor Modular de Internacionalización (i18n)
const I18nManager = {
    locales: {},
    currentLang: localStorage.getItem("ui_lang") || "es",
    isLoaded: false,

    async init() {
        try {
            const res = await fetch("/static/locales.json");
            if (res.ok) {
                this.locales = await res.json();
                this.isLoaded = true;
            }
        } catch (e) {
            console.warn("No se pudo cargar /static/locales.json:", e);
        }

        const sel = document.getElementById("ui-lang-select");
        if (sel) {
            sel.value = this.currentLang;
            sel.addEventListener("change", (e) => {
                this.setLanguage(e.target.value);
            });
        }

        this.applyLanguage(this.currentLang);
    },

    t(key) {
        const langDict = this.locales[this.currentLang] || this.locales["es"] || {};
        return langDict[key] || key;
    },

    setLanguage(lang) {
        this.currentLang = lang;
        localStorage.setItem("ui_lang", lang);
        this.applyLanguage(lang);
    },

    applyLanguage(lang) {
        const t = this.locales[lang] || this.locales["es"];
        if (!t) return;

        const sel = document.getElementById("ui-lang-select");
        if (sel) sel.value = lang;

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
        if (callBtnText) {
            callBtnText.innerText = window.isCallMode ? t.call_btn_stop : t.call_btn_start;
        }

        const micBtnLabel = document.getElementById("mic-btn-label");
        if (micBtnLabel) {
            micBtnLabel.innerText = window.isRecording ? t.mic_btn_listening : t.mic_btn_speak;
        }

        const interruptBtn = document.getElementById("interrupt-btn");
        if (interruptBtn) interruptBtn.innerText = t.interrupt_btn;

        const lMic = document.getElementById("label-mic");
        const lVoice = document.getElementById("label-voice");
        const lVad = document.getElementById("label-vad");
        const lPers = document.getElementById("label-personality");
        if (lMic) lMic.innerText = t.label_mic;
        if (lVoice) lVoice.innerText = t.label_voice;
        if (lVad) lVad.innerText = t.label_vad;
        if (lPers && t.label_personality) lPers.innerText = t.label_personality;

        const personalitySelect = document.getElementById("personality-select");
        if (personalitySelect && t.pers_coach) {
            const optCoach = personalitySelect.querySelector('option[value="coach"]');
            const optFriend = personalitySelect.querySelector('option[value="friendly"]');
            const optTech = personalitySelect.querySelector('option[value="tech"]');
            const optExec = personalitySelect.querySelector('option[value="executive"]');
            if (optCoach) optCoach.innerText = t.pers_coach;
            if (optFriend) optFriend.innerText = t.pers_friendly;
            if (optTech) optTech.innerText = t.pers_tech;
            if (optExec) optExec.innerText = t.pers_executive;
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
    }
};

window.I18nManager = I18nManager;
