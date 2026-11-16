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
const visualizerCanvas = document.getElementById("audio-visualizer-canvas");
const visualizerCtx = visualizerCanvas ? visualizerCanvas.getContext("2d") : null;
let micAnalyser = null;
let visualizerAnimationId = null;
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

let currentPartialBubble = null;
let currentPartialTextEl = null;

// ==========================================
// INTERNACIONALIZACIÓN Y MULTIIDIOMA UI (i18n)
// ==========================================
const I18N = {
    es: {
        mode_en: "🇺🇸 Practicar Inglés",
        mode_es: "🇪🇸 Español",
        mode_auto: "🌐 Bilingüe / Auto",
        connecting: "Conectando...",
        connected: "Conectado (Local)",
        disconnected: "Desconectado. Reintentando...",
        orb_ready: "Listo para conversar",
        orb_listening: "📞 Te escucho...",
        orb_speaking: "Hablando...",
        orb_thinking: "Pensando respuesta...",
        welcome_title: "👋 ¡Bienvenido a tu Sala de Voz con IA Local!",
        welcome_desc: "Habla libremente con naturalidad. Verás la transcripción en vivo palabra por palabra, traducciones, notas guardadas y feedback en tiempo real.",
        tip_no_limits: "💡 Sin límites de tiempo",
        tip_offline: "⚡ 100% Local y privado",
        tip_memory: "🎯 Memoria RAG y herramientas",
        input_placeholder_en: "Escribe un mensaje en inglés...",
        input_placeholder_es: "Escribe un mensaje en español...",
        input_placeholder_auto: "Escribe o habla en inglés o español...",
        call_btn_start: "Iniciar Modo Llamada (Manos Libres)",
        call_btn_stop: "Finalizar Modo Llamada",
        label_mic: "🎤 Mic:",
        label_voice: "🗣️ Voz IA:",
        label_vad: "🎚️ Filtro VAD:",
        label_personality: "🎭 Personalidad:",
        pers_coach: "🎓 Tutor de Idiomas",
        pers_friendly: "🤗 Amigo Casual",
        pers_tech: "💻 Senior Tech Lead",
        pers_executive: "👔 Mentor Ejecutivo",
        vad_low: "Baja (Filtra respiración fuerte y ventilador)",
        vad_med: "Media (Recomendada)",
        vad_high: "Alta (Habla muy suave)",
        mic_btn_speak: "Pulsar para hablar",
        mic_btn_listening: "Escuchando...",
        interrupt_btn: "⏹ Interrumpir",
        meter_label: "Nivel de voz:",
        panel_coaching: "🎯 Tutor Feedback & Grammar",
        panel_coaching_empty: "Habla en inglés para recibir observaciones gramaticales y sugerencias de vocabulario en tiempo real.",
        panel_vocab: "📝 Vocabulario & Frases",
        panel_vocab_empty: "Aquí se guardarán las oraciones clave de la sesión.",
        panel_notes: "📌 Notas Rápidas por Voz",
        panel_notes_empty: 'Di "Toma nota de..." o "Recuérdame..." para guardar notas por voz.',
        panel_metrics: "⚡ Rendimiento en Tiempo Real",
        metric_time: "Hora último mensaje:",
        metric_stt: "Whisper STT (Voz):",
        metric_ttfa: "Latencia 1er Audio (TTFA):",
        metric_total: "Tiempo Total Respuesta:",
        metric_vram: "VRAM Utilizada:",
        tool_badge: "🔧 Herramienta: ",
        clear_confirm: "¿Deseas vaciar la base de datos de conversaciones, notas y vocabulario guardado?",
        clear_done: "Historial, notas y vocabulario limpiados."
    },
    en: {
        mode_en: "🇺🇸 Practice English",
        mode_es: "🇪🇸 Spanish Assistant",
        mode_auto: "🌐 Bilingual / Auto",
        connecting: "Connecting...",
        connected: "Connected (Local)",
        disconnected: "Disconnected. Retrying...",
        orb_ready: "Ready to converse",
        orb_listening: "📞 Listening to you...",
        orb_speaking: "Speaking...",
        orb_thinking: "Thinking response...",
        welcome_title: "👋 Welcome to your Local AI Voice Room!",
        welcome_desc: "Speak naturally and freely. You will see live word-by-word transcription, translations, saved voice notes, and real-time coaching feedback.",
        tip_no_limits: "💡 No time limits",
        tip_offline: "⚡ 100% Local & private",
        tip_memory: "🎯 RAG Memory & Voice Tools",
        input_placeholder_en: "Type a message in English...",
        input_placeholder_es: "Type a message in Spanish...",
        input_placeholder_auto: "Type or speak in English or Spanish...",
        call_btn_start: "Start Call Mode (Hands-Free)",
        call_btn_stop: "End Call Mode",
        label_mic: "🎤 Mic:",
        label_voice: "🗣️ AI Voice:",
        label_vad: "🎚️ VAD Filter:",
        label_personality: "🎭 Personality:",
        pers_coach: "🎓 Language Coach",
        pers_friendly: "🤗 Casual Friend",
        pers_tech: "💻 Senior Tech Lead",
        pers_executive: "👔 Executive Advisor",
        vad_low: "Low (Filters heavy breathing & fan)",
        vad_med: "Medium (Recommended)",
        vad_high: "High (Soft speech)",
        mic_btn_speak: "Click to speak",
        mic_btn_listening: "Listening...",
        interrupt_btn: "⏹ Interrupt",
        meter_label: "Voice level:",
        panel_coaching: "🎯 Coaching Feedback & Grammar",
        panel_coaching_empty: "Speak in English to receive grammar feedback and vocabulary suggestions in real time.",
        panel_vocab: "📝 Vocabulary & Phrases",
        panel_vocab_empty: "Key phrases from your session will appear here.",
        panel_notes: "📌 Quick Voice Notes",
        panel_notes_empty: 'Say "Take a note..." or "Remember that..." to save notes by voice.',
        panel_metrics: "⚡ Real-Time Performance",
        metric_time: "Last message time:",
        metric_stt: "Whisper STT (Speech):",
        metric_ttfa: "First Audio Latency (TTFA):",
        metric_total: "Total Response Time:",
        metric_vram: "VRAM Utilized:",
        tool_badge: "🔧 Tool: ",
        clear_confirm: "Do you want to clear the local database of conversations, notes, and saved vocabulary?",
        clear_done: "History, notes, and vocabulary cleared."
    },
    pt: {
        mode_en: "🇺🇸 Praticar Inglês",
        mode_es: "🇪🇸 Assistente Espanhol",
        mode_auto: "🌐 Bilíngue / Auto",
        connecting: "Conectando...",
        connected: "Conectado (Local)",
        disconnected: "Desconectado. Tentando novamente...",
        orb_ready: "Pronto para conversar",
        orb_listening: "📞 Ouvindo você...",
        orb_speaking: "Falando...",
        orb_thinking: "Pensando na resposta...",
        welcome_title: "👋 Bem-vindo à sua Sala de Voz IA Local!",
        welcome_desc: "Fale naturalmente. Você verá transcrição ao vivo palavra por palavra, notas salvas e feedback em tempo real.",
        tip_no_limits: "💡 Sem limites de tempo",
        tip_offline: "⚡ 100% Local e privado",
        tip_memory: "🎯 Memória RAG e ferramentas por voz",
        input_placeholder_en: "Digite uma mensagem em inglês...",
        input_placeholder_es: "Digite uma mensagem em espanhol...",
        input_placeholder_auto: "Digite ou fale em qualquer idioma...",
        call_btn_start: "Iniciar Modo Chamada (Mãos Livres)",
        call_btn_stop: "Encerrar Modo Chamada",
        label_mic: "🎤 Microfone:",
        label_voice: "🗣️ Voz da IA:",
        label_vad: "🎚️ Filtro VAD:",
        label_personality: "🎭 Personalidade:",
        pers_coach: "🎓 Tutor de Idiomas",
        pers_friendly: "🤗 Amigo Casual",
        pers_tech: "💻 Senior Tech Lead",
        pers_executive: "👔 Mentor Executivo",
        vad_low: "Baixa (Filtra respiração forte e ventilador)",
        vad_med: "Média (Recomendada)",
        vad_high: "Alta (Fala suave)",
        mic_btn_speak: "Clique para falar",
        mic_btn_listening: "Ouvindo...",
        interrupt_btn: "⏹ Interromper",
        meter_label: "Nível de voz:",
        panel_coaching: "🎯 Feedback do Tutor & Gramática",
        panel_coaching_empty: "Fale em inglês para receber observações gramaticais em tempo real.",
        panel_vocab: "📝 Vocabulário & Frases",
        panel_vocab_empty: "As frases-chave da sessão serão salvas aqui.",
        panel_notes: "📌 Notas Rápidas de Voz",
        panel_notes_empty: 'Diga "Anote que..." ou "Lembre-me de..." para salvar notas.',
        panel_metrics: "⚡ Desempenho em Tempo Real",
        metric_time: "Hora da última mensagem:",
        metric_stt: "Whisper STT (Voz):",
        metric_ttfa: "Latência do 1º Áudio (TTFA):",
        metric_total: "Tempo Total de Resposta:",
        metric_vram: "VRAM Utilizada:",
        tool_badge: "🔧 Ferramenta: ",
        clear_confirm: "Deseja limpar todo o histórico de conversas, notas e vocabulário?",
        clear_done: "Histórico e notas limpos."
    },
    fr: {
        mode_en: "🇺🇸 Pratiquer l'anglais",
        mode_es: "🇪🇸 Assistant espagnol",
        mode_auto: "🌐 Bilingue / Auto",
        connecting: "Connexion...",
        connected: "Connecté (Local)",
        disconnected: "Déconnecté. Nouvelle tentative...",
        orb_ready: "Prêt à converser",
        orb_listening: "📞 Je vous écoute...",
        orb_speaking: "Parle...",
        orb_thinking: "Réflexion en cours...",
        welcome_title: "👋 Bienvenue dans votre salon vocal IA local !",
        welcome_desc: "Parlez naturellement. Vous verrez la transcription mot à mot en direct, les traductions et les notes vocales.",
        tip_no_limits: "💡 Sans limite de temps",
        tip_offline: "⚡ 100% Local et privé",
        tip_memory: "🎯 Mémoire RAG et outils vocaux",
        input_placeholder_en: "Tapez un message en anglais...",
        input_placeholder_es: "Tapez un message en espagnol...",
        input_placeholder_auto: "Tapez ou parlez librement...",
        call_btn_start: "Mode Appel Mains Libres",
        call_btn_stop: "Terminer l'appel",
        label_mic: "🎤 Micro :",
        label_voice: "🗣️ Voix IA :",
        label_vad: "🎚️ Filtre VAD :",
        label_personality: "🎭 Personnalité :",
        pers_coach: "🎓 Coach de Langue",
        pers_friendly: "🤗 Ami Proche",
        pers_tech: "💻 Senior Tech Lead",
        pers_executive: "👔 Conseiller Exécutif",
        vad_low: "Faible (Filtre bruits et souffle)",
        vad_med: "Moyen (Recommandé)",
        vad_high: "Élevé (Voix douce)",
        mic_btn_speak: "Cliquer pour parler",
        mic_btn_listening: "Écoute en cours...",
        interrupt_btn: "⏹ Interrompre",
        meter_label: "Niveau vocal :",
        panel_coaching: "🎯 Coaching & Grammaire",
        panel_coaching_empty: "Parlez en anglais pour recevoir des corrections en temps réel.",
        panel_vocab: "📝 Vocabulaire & Phrases",
        panel_vocab_empty: "Les phrases clés de la session seront enregistrées ici.",
        panel_notes: "📌 Notes Vocales Rapides",
        panel_notes_empty: 'Dites "Prends note de..." pour enregistrer une note.',
        panel_metrics: "⚡ Performances en Direct",
        metric_time: "Dernier message :",
        metric_stt: "Whisper STT (Voix) :",
        metric_ttfa: "Latence 1er Audio (TTFA) :",
        metric_total: "Temps Total :",
        metric_vram: "VRAM Utilisée :",
        tool_badge: "🔧 Outil : ",
        clear_confirm: "Voulez-vous effacer l'historique, les notes et le vocabulaire ?",
        clear_done: "Historique et notes effacés."
    },
    de: {
        mode_en: "🇺🇸 Englisch üben",
        mode_es: "🇪🇸 Spanisch-Assistent",
        mode_auto: "🌐 Zweisprachig / Auto",
        connecting: "Verbinde...",
        connected: "Verbunden (Lokal)",
        disconnected: "Getrennt. Wiederhole...",
        orb_ready: "Bereit zum Gespräch",
        orb_listening: "📞 Ich höre zu...",
        orb_speaking: "Spricht...",
        orb_thinking: "Denkt nach...",
        welcome_title: "👋 Willkommen im lokalen KI-Sprachraum!",
        welcome_desc: "Sprechen Sie ganz natürlich. Sie sehen Live-Transkriptionen Wort für Wort, Notizen und Coaching in Echtzeit.",
        tip_no_limits: "💡 Kein Zeitlimit",
        tip_offline: "⚡ 100% Lokal & privat",
        tip_memory: "🎯 RAG-Gedächtnis & Sprach-Tools",
        input_placeholder_en: "Schreiben Sie auf Englisch...",
        input_placeholder_es: "Schreiben Sie auf Spanisch...",
        input_placeholder_auto: "Schreiben oder sprechen Sie frei...",
        call_btn_start: "Anrufmodus starten (Freisprechen)",
        call_btn_stop: "Anrufmodus beenden",
        label_mic: "🎤 Mikrofon:",
        label_voice: "🗣️ KI-Stimme:",
        label_vad: "🎚️ VAD-Filter:",
        label_personality: "🎭 Persönlichkeit:",
        pers_coach: "🎓 Sprachcoach",
        pers_friendly: "🤗 Guter Freund",
        pers_tech: "💻 Senior Tech Lead",
        pers_executive: "👔 Executive Berater",
        vad_low: "Niedrig (Filtert Atemgeräusche)",
        vad_med: "Mittel (Empfohlen)",
        vad_high: "Hoch (Leise Sprache)",
        mic_btn_speak: "Klicken zum Sprechen",
        mic_btn_listening: "Zuhören...",
        interrupt_btn: "⏹ Unterbrechen",
        meter_label: "Sprachpegel:",
        panel_coaching: "🎯 Coaching & Grammatik",
        panel_coaching_empty: "Sprechen Sie auf Englisch, um Grammatiktipps in Echtzeit zu erhalten.",
        panel_vocab: "📝 Vokabeln & Sätze",
        panel_vocab_empty: "Wichtige Sätze werden hier gespeichert.",
        panel_notes: "📌 Schnelle Sprachnotizen",
        panel_notes_empty: 'Sagen Sie "Notiere..." um eine Notiz zu speichern.',
        panel_metrics: "⚡ Echtzeit-Metriken",
        metric_time: "Letzte Nachricht:",
        metric_stt: "Whisper STT (Sprache):",
        metric_ttfa: "Erste Audio-Latenz (TTFA):",
        metric_total: "Gesamte Antwortzeit:",
        metric_vram: "VRAM-Nutzung:",
        tool_badge: "🔧 Werkzeug: ",
        clear_confirm: "Möchten Sie den gesamten Verlauf, Notizen und Vokabeln löschen?",
        clear_done: "Verlauf und Notizen gelöscht."
    },
    it: {
        mode_en: "🇺🇸 Pratica l'inglese",
        mode_es: "🇪🇸 Assistente spagnolo",
        mode_auto: "🌐 Bilingue / Auto",
        connecting: "Connessione...",
        connected: "Connesso (Locale)",
        disconnected: "Disconnesso. Riconnessione...",
        orb_ready: "Pronto a conversare",
        orb_listening: "📞 Ti ascolto...",
        orb_speaking: "Parlando...",
        orb_thinking: "Elaborazione risposta...",
        welcome_title: "👋 Benvenuto nella tua stanza vocale IA locale!",
        welcome_desc: "Parla liberamente. Vedrai la trascrizione parola per parola in tempo reale, note salvate e feedback.",
        tip_no_limits: "💡 Nessun limite di tempo",
        tip_offline: "⚡ 100% Locale e privato",
        tip_memory: "🎯 Memoria RAG e strumenti vocali",
        input_placeholder_en: "Scrivi un messaggio in inglese...",
        input_placeholder_es: "Scrivi un messaggio in spagnolo...",
        input_placeholder_auto: "Scrivi o parla liberamente...",
        call_btn_start: "Avvia Modalità Chiamata (Vivavoce)",
        call_btn_stop: "Termina Chiamata",
        label_mic: "🎤 Microfono:",
        label_voice: "🗣️ Voce IA:",
        label_vad: "🎚️ Filtro VAD:",
        label_personality: "🎭 Personalità:",
        pers_coach: "🎓 Tutor Linguistico",
        pers_friendly: "🤗 Amico Informale",
        pers_tech: "💻 Senior Tech Lead",
        pers_executive: "👔 Mentor Esecutivo",
        vad_low: "Bassa (Filtra respiro forte e ventole)",
        vad_med: "Media (Consigliata)",
        vad_high: "Alta (Voce bassa)",
        mic_btn_speak: "Clicca per parlare",
        mic_btn_listening: "In ascolto...",
        interrupt_btn: "⏹ Interrompi",
        meter_label: "Livello voce:",
        panel_coaching: "🎯 Feedback del Tutor & Grammatica",
        panel_coaching_empty: "Parla in inglese per ricevere suggerimenti grammaticali immediati.",
        panel_vocab: "📝 Vocabolario & Frasi",
        panel_vocab_empty: "Le frasi chiave della sessione appariranno qui.",
        panel_notes: "📌 Note Vocali Rapide",
        panel_notes_empty: 'Dì "Prendi nota di..." per salvare le tue note.',
        panel_metrics: "⚡ Prestazioni in Tempo Reale",
        metric_time: "Ultimo messaggio:",
        metric_stt: "Whisper STT (Voce):",
        metric_ttfa: "Latenza 1º Audio (TTFA):",
        metric_total: "Tempo Totale:",
        metric_vram: "VRAM Utilizzata:",
        tool_badge: "🔧 Strumento: ",
        clear_confirm: "Vuoi cancellare la cronologia, le note e il vocabolario?",
        clear_done: "Cronologia e note cancellate."
    },
    ja: {
        mode_en: "🇺🇸 英語の練習",
        mode_es: "🇪🇸 スペイン語アシスタント",
        mode_auto: "🌐 バイリンガル / 自動",
        connecting: "接続中...",
        connected: "接続済み (ローカル)",
        disconnected: "切断されました。再試行中...",
        orb_ready: "会話の準備完了",
        orb_listening: "📞 聞いています...",
        orb_speaking: "発話中...",
        orb_thinking: "考え中...",
        welcome_title: "👋 ローカルAI音声ルームへようこそ！",
        welcome_desc: "自由に話しかけてください。リアルタイムの文字起こし、音声メモ、文法フィードバックが表示されます。",
        tip_no_limits: "💡 時間無制限",
        tip_offline: "⚡ 完全ローカル＆プライベート",
        tip_memory: "🎯 RAGメモリ＆音声ツール",
        input_placeholder_en: "英語でメッセージを入力...",
        input_placeholder_es: "スペイン語でメッセージを入力...",
        input_placeholder_auto: "文字入力またはマイクで発話...",
        call_btn_start: "通話モード開始 (ハンズフリー)",
        call_btn_stop: "通話を終了",
        label_mic: "🎤 マイク:",
        label_voice: "🗣️ AI音声:",
        label_vad: "🎚️ VAD感度:",
        label_personality: "🎭 性格 / ペルソナ:",
        pers_coach: "🎓 語学コーチ",
        pers_friendly: "🤗 親しい友人",
        pers_tech: "💻 シニアテックリード",
        pers_executive: "👔 エグゼクティブ顧問",
        vad_low: "低 (呼吸音やファンをカット)",
        vad_med: "中 (推奨)",
        vad_high: "高 (小声用)",
        mic_btn_speak: "クリックして話す",
        mic_btn_listening: "聞き取り中...",
        interrupt_btn: "⏹ 割り込み中断",
        meter_label: "音声レベル:",
        panel_coaching: "🎯 チューター指導＆文法",
        panel_coaching_empty: "英語で話すとリアルタイムで文法と表現のアドバイスが表示されます。",
        panel_vocab: "📝 語彙＆フレーズ",
        panel_vocab_empty: "練習した重要フレーズがここに保存されます。",
        panel_notes: "📌 音声クイックメモ",
        panel_notes_empty: "「〜をメモして」と言うと音声でメモを保存できます。",
        panel_metrics: "⚡ リアルタイム性能メトリクス",
        metric_time: "最終発言時刻:",
        metric_stt: "Whisper STT (音声認識):",
        metric_ttfa: "初回音声遅延 (TTFA):",
        metric_total: "合計応答時間:",
        metric_vram: "使用VRAM:",
        tool_badge: "🔧 ツール: ",
        clear_confirm: "すべての履歴、メモ、単語データを削除しますか？",
        clear_done: "履歴とメモを削除しました。"
    },
    zh: {
        mode_en: "🇺🇸 练习英语",
        mode_es: "🇪🇸 西班牙语助手",
        mode_auto: "🌐 双语 / 自动",
        connecting: "正在连接...",
        connected: "已连接 (本地)",
        disconnected: "已断开连接。重试中...",
        orb_ready: "随时可以对话",
        orb_listening: "📞 正在聆听...",
        orb_speaking: "正在说话...",
        orb_thinking: "正在思考...",
        welcome_title: "👋 欢迎进入本地AI语音对话室！",
        welcome_desc: "请自然开口说话。您将看到实时的逐词转录、双语翻译、语音笔记及语法纠错反馈。",
        tip_no_limits: "💡 无时间限制",
        tip_offline: "⚡ 100% 本地运行与隐私保护",
        tip_memory: "🎯 RAG长期记忆与语音工具调用",
        input_placeholder_en: "输入英文消息...",
        input_placeholder_es: "输入西班牙语消息...",
        input_placeholder_auto: "键盘输入或直接按麦克风说话...",
        call_btn_start: "开启通话模式 (免提连续对话)",
        call_btn_stop: "结束通话",
        label_mic: "🎤 麦克风:",
        label_voice: "🗣️ AI声音:",
        label_vad: "🎚️ VAD静音阈值:",
        label_personality: "🎭 导师人设:",
        pers_coach: "🎓 语言教练",
        pers_friendly: "🤗 挚友伙伴",
        pers_tech: "💻 资深技术专家",
        pers_executive: "👔 高管战略导师",
        vad_low: "低 (过滤粗重呼吸与风扇噪音)",
        vad_med: "中 (推荐标准)",
        vad_high: "高 (适合低声耳语)",
        mic_btn_speak: "按住说话",
        mic_btn_listening: "正在聆听...",
        interrupt_btn: "⏹ 打断AI发音",
        meter_label: "音频音量:",
        panel_coaching: "🎯 导师指导与语法教学",
        panel_coaching_empty: "使用英语说话可实时获得语法纠错与表达建议。",
        panel_vocab: "📝 词汇与重点句型",
        panel_vocab_empty: "本次对话的关键句子将自动保存在这里。",
        panel_notes: "📌 语音快速备忘录",
        panel_notes_empty: '请说 "帮我记下..." 即可通过语音保存备忘。',
        panel_metrics: "⚡ 实时推理性能指标",
        metric_time: "最后消息时间:",
        metric_stt: "Whisper语音识别 (STT):",
        metric_ttfa: "首句出声延迟 (TTFA):",
        metric_total: "总计响应耗时:",
        metric_vram: "显存占用 (VRAM):",
        tool_badge: "🔧 调用工具: ",
        clear_confirm: "确定要清空本地数据库中的所有历史记录、备忘与词汇吗？",
        clear_done: "历史与备忘已成功清空。"
    }
};

let currentUiLang = localStorage.getItem("ui_lang") || "es";

function setUiLanguage(lang) {
    currentUiLang = lang;
    localStorage.setItem("ui_lang", lang);
    const t = I18N[lang] || I18N.es;

    const sel = document.getElementById("ui-lang-select");
    if (sel) {
        sel.value = lang;
    }

    const btnEs = document.getElementById("ui-lang-es");
    const btnEn = document.getElementById("ui-lang-en");
    if (btnEs && btnEn) {
        btnEs.classList.toggle("active", lang === "es");
        btnEn.classList.toggle("active", lang === "en");
    }

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

    if (textInput) {
        if (currentLanguageMode === "es") textInput.placeholder = t.input_placeholder_es;
        else if (currentLanguageMode === "en") textInput.placeholder = t.input_placeholder_en;
        else textInput.placeholder = t.input_placeholder_auto;
    }

    if (callBtnText) {
        callBtnText.innerText = isCallMode ? t.call_btn_stop : t.call_btn_start;
    }
    if (micBtnLabel) {
        micBtnLabel.innerText = isRecording ? t.mic_btn_listening : t.mic_btn_speak;
    }
    if (interruptBtn) {
        interruptBtn.innerText = t.interrupt_btn;
    }

    const lMic = document.getElementById("label-mic");
    const lVoice = document.getElementById("label-voice");
    const lVad = document.getElementById("label-vad");
    const lPers = document.getElementById("label-personality");
    if (lMic) lMic.innerText = t.label_mic;
    if (lVoice) lVoice.innerText = t.label_voice;
    if (lVad) lVad.innerText = t.label_vad;
    if (lPers && t.label_personality) lPers.innerText = t.label_personality;

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

    if (orbLabel && !isAudioPlaying && !isRecording) {
        orbLabel.innerText = t.orb_ready;
    }
}

function getFormattedTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
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
        setTimeout(connectWebSocket, 2000);
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
// VISUALIZADOR DE AUDIO 60 FPS (CANVAS)
// ==========================================

function drawVisualizer() {
    if (!visualizerCanvas || !visualizerCtx) return;
    visualizerAnimationId = requestAnimationFrame(drawVisualizer);

    const width = visualizerCanvas.width;
    const height = visualizerCanvas.height;
    visualizerCtx.clearRect(0, 0, width, height);
    const centerY = height / 2;

    if (isAudioPlaying) {
        // AI Speaking: Multi-harmonic luminous wave
        const time = Date.now() * 0.005;
        visualizerCtx.lineWidth = 2.5;
        visualizerCtx.strokeStyle = "#a855f7"; // violet
        visualizerCtx.shadowBlur = 12;
        visualizerCtx.shadowColor = "#c084fc";

        visualizerCtx.beginPath();
        for (let x = 0; x < width; x++) {
            const progress = x / width;
            const envelope = Math.sin(progress * Math.PI);
            const y = centerY + Math.sin(x * 0.04 + time * 3) * 16 * envelope
                              + Math.sin(x * 0.08 - time * 2) * 8 * envelope;
            if (x === 0) visualizerCtx.moveTo(x, y);
            else visualizerCtx.lineTo(x, y);
        }
        visualizerCtx.stroke();

        // Second wave: cyan harmonic
        visualizerCtx.strokeStyle = "#06b6d4";
        visualizerCtx.shadowColor = "#38bdf8";
        visualizerCtx.beginPath();
        for (let x = 0; x < width; x++) {
            const progress = x / width;
            const envelope = Math.sin(progress * Math.PI);
            const y = centerY + Math.sin(x * 0.05 - time * 2.5) * 12 * envelope
                              + Math.cos(x * 0.03 + time) * 6 * envelope;
            if (x === 0) visualizerCtx.moveTo(x, y);
            else visualizerCtx.lineTo(x, y);
        }
        visualizerCtx.stroke();

    } else if (micAnalyser && (isRecording || isUserSpeakingInCall)) {
        // User Speaking: Real-time frequency / time-domain waveform
        const bufferLength = micAnalyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        micAnalyser.getByteTimeDomainData(dataArray);

        visualizerCtx.lineWidth = 2.5;
        visualizerCtx.strokeStyle = "#10b981"; // emerald
        visualizerCtx.shadowBlur = 12;
        visualizerCtx.shadowColor = "#34d399";

        visualizerCtx.beginPath();
        const sliceWidth = width / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const progress = i / bufferLength;
            const envelope = Math.sin(progress * Math.PI);
            const y = centerY + (v - 1.0) * (height / 2) * 1.6 * envelope;

            if (i === 0) visualizerCtx.moveTo(x, y);
            else visualizerCtx.lineTo(x, y);

            x += sliceWidth;
        }
        visualizerCtx.lineTo(width, centerY);
        visualizerCtx.stroke();

    } else {
        // Idle: Soft ambient breathing sine
        const time = Date.now() * 0.002;
        visualizerCtx.lineWidth = 1.5;
        visualizerCtx.strokeStyle = "rgba(59, 130, 246, 0.45)";
        visualizerCtx.shadowBlur = 6;
        visualizerCtx.shadowColor = "rgba(59, 130, 246, 0.5)";

        visualizerCtx.beginPath();
        for (let x = 0; x < width; x++) {
            const progress = x / width;
            const envelope = Math.sin(progress * Math.PI);
            const y = centerY + Math.sin(x * 0.03 + time) * 5 * envelope;
            if (x === 0) visualizerCtx.moveTo(x, y);
            else visualizerCtx.lineTo(x, y);
        }
        visualizerCtx.stroke();
    }
}

function startVisualizerLoop() {
    if (!visualizerAnimationId) {
        drawVisualizer();
    }
}

// ==========================================
// ENCODIFICADOR WAV 16kHz MONO
// ==========================================

function encodeWAV(samples, sampleRate = 16000) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([view], { type: 'audio/wav' });
}

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

        micAnalyser = audioContext.createAnalyser();
        micAnalyser.fftSize = 256;
        source.connect(micAnalyser);

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

window.addEventListener("DOMContentLoaded", () => {
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

    // Selector de modo de idioma
    document.querySelectorAll(".lang-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentLanguageMode = btn.dataset.mode;

            // Auto-seleccionar la mejor voz para el modo
            if (voiceSelect) {
                if (currentLanguageMode === "es" && !voiceSelect.value.startsWith("e")) {
                    voiceSelect.value = "ef_dora";
                } else if (currentLanguageMode === "en" && !voiceSelect.value.startsWith("a")) {
                    voiceSelect.value = "af_sarah";
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

    // Iniciar loop del visualizador de frecuencias 60 FPS
    startVisualizerLoop();

    // Inicializar datos persistentes e idioma UI en el arranque
    setUiLanguage(currentUiLang);
    loadUserProfile();
    loadPersistentVocabulary();
    loadPersistentNotes();
    loadPersistentHistory();

    const clearHistoryBtn = document.getElementById("clear-history-btn");
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener("click", async () => {
            if (confirm("¿Deseas vaciar la base de datos de conversaciones, notas y vocabulario guardado?")) {
                try {
                    await fetch("/api/history", { method: "DELETE" });
                    if (vocabularyList) {
                        vocabularyList.innerHTML = '<div class="empty-tip">Historial y vocabulario limpiados.</div>';
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
