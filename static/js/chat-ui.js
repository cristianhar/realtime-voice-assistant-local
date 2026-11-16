// ==============================================================================
// Voice Assistant - Chat UI Manager (Bubbles, Tools, Translations & Orb)
// ==============================================================================

class ChatUIManager {
    constructor(elements = {}) {
        this.chatMessages = elements.chatMessages || document.getElementById("chat-messages");
        this.voiceOrb = elements.voiceOrb || document.getElementById("voice-orb");
        this.orbLabel = elements.orbLabel || document.getElementById("orb-label");
        this.coachingContent = elements.coachingContent || document.getElementById("coaching-content");
        this.vocabularyList = elements.vocabularyList || document.getElementById("vocabulary-list");
        this.metricTime = elements.metricTime || document.getElementById("metric-time");

        this.currentPartialBubble = null;
        this.currentPartialTextEl = null;
    }

    escapeHtml(text) {
        const div = document.createElement("div");
        div.innerText = text;
        return div.innerHTML;
    }

    getFormattedTime() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    setOrbState(state, label) {
        if (this.voiceOrb) this.voiceOrb.className = `voice-orb ${state}`;
        if (label && this.orbLabel) this.orbLabel.innerText = label;
    }

    showSystemNotification(msg) {
        if (!this.chatMessages) return;
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
        this.chatMessages.appendChild(notice);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showSecureContextModal(httpsUrl) {
        if (document.getElementById("secure-context-alert")) {
            document.getElementById("secure-context-alert").scrollIntoView({ behavior: "smooth" });
            return;
        }

        const card = document.createElement("div");
        card.id = "secure-context-alert";
        card.className = "secure-context-card";
        card.innerHTML = `
            <div class="secure-context-header">
                <span class="secure-icon" style="font-size: 1.4rem;">🔒</span>
                <strong>Micrófono bloqueado en tu Celular</strong>
            </div>
            <p class="secure-context-desc">
                Por política de seguridad móvil, Chrome y Safari <b>bloquean el micrófono en páginas HTTP</b>. Para hablar debes acceder vía <b>HTTPS</b>:
            </p>
            <div class="secure-context-actions">
                <a href="${httpsUrl}" class="secure-btn-primary">
                    🚀 Entrar con HTTPS (${httpsUrl})
                </a>
            </div>
            <div class="secure-context-help">
                <strong>📋 Pasos para entrar (5 segundos):</strong><br>
                1. Toca el botón azul de arriba.<br>
                2. Verás <i>"La conexión no es privada"</i>.<br>
                3. Toca en <b>"Configuración avanzada"</b> y luego en <b>"Acceder (no seguro)"</b>.<br>
                4. ¡Listo! El micrófono funcionará de inmediato.
            </div>
        `;
        if (this.chatMessages) {
            this.chatMessages.appendChild(card);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    updateUserPartialBubble(partialText, lang, currentLangMode) {
        if (!this.chatMessages) return;
        if (!this.currentPartialBubble) {
            const timeStr = this.getFormattedTime();
            if (this.metricTime) this.metricTime.innerText = timeStr;

            this.currentPartialBubble = document.createElement("div");
            this.currentPartialBubble.className = "message-bubble user partial";

            let roleLabel = "👤 You (English)";
            if (currentLangMode === "es") {
                roleLabel = "👤 Tú (Español)";
            } else if (currentLangMode === "auto") {
                roleLabel = `👤 You / Tú [${lang ? lang.toUpperCase() : "AUTO"}]`;
            }

            this.currentPartialBubble.innerHTML = `
                <div class="bubble-header">
                    <span class="bubble-role">${roleLabel}</span>
                    <span class="bubble-time">${timeStr} <span class="live-dot">● En vivo</span></span>
                </div>
                <div class="bubble-text-en"></div>
            `;
            this.chatMessages.appendChild(this.currentPartialBubble);
            this.currentPartialTextEl = this.currentPartialBubble.querySelector(".bubble-text-en");
        }

        if (this.currentPartialTextEl) {
            this.currentPartialTextEl.innerText = partialText + " ...";
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    createUserBubble(text, latency, lang, turnId, currentLangMode) {
        const timeStr = this.getFormattedTime();
        if (this.metricTime) this.metricTime.innerText = timeStr;

        const showTranslation = currentLangMode === "en";

        let roleLabel = "👤 You (English)";
        if (currentLangMode === "es") {
            roleLabel = "👤 Tú (Español)";
        } else if (currentLangMode === "auto") {
            roleLabel = `👤 You / Tú [${lang ? lang.toUpperCase() : "AUTO"}]`;
        }

        let bubble = this.currentPartialBubble;

        if (bubble) {
            bubble.classList.remove("partial");
            bubble.id = `user-bubble-${turnId}`;
            bubble.innerHTML = `
                <div class="bubble-header">
                    <span class="bubble-role">${roleLabel}</span>
                    <span class="bubble-time">${timeStr}</span>
                </div>
                <div class="bubble-text-en">${this.escapeHtml(text)}</div>
                ${showTranslation ? `<div class="bubble-text-es"><span>🇪🇸</span> <span id="user-tr-${turnId}" class="translation-placeholder">Traduciendo...</span></div>` : ""}
                ${latency ? `<div class="bubble-meta"><span>🎙️ STT: ${latency} ms</span></div>` : ""}
            `;
        } else if (this.chatMessages) {
            bubble = document.createElement("div");
            bubble.className = "message-bubble user";
            bubble.id = `user-bubble-${turnId}`;
            bubble.innerHTML = `
                <div class="bubble-header">
                    <span class="bubble-role">${roleLabel}</span>
                    <span class="bubble-time">${timeStr}</span>
                </div>
                <div class="bubble-text-en">${this.escapeHtml(text)}</div>
                ${showTranslation ? `<div class="bubble-text-es"><span>🇪🇸</span> <span id="user-tr-${turnId}" class="translation-placeholder">Traduciendo...</span></div>` : ""}
                ${latency ? `<div class="bubble-meta"><span>🎙️ STT: ${latency} ms</span></div>` : ""}
            `;
            this.chatMessages.appendChild(bubble);
        }

        this.currentPartialBubble = null;
        this.currentPartialTextEl = null;

        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
        this.addToVocabulary(text);

        // Crear burbuja de respuesta del asistente
        let aiRoleLabel = "🤖 AI Tutor (English)";
        if (currentLangMode === "es") {
            aiRoleLabel = "🤖 Asistente (Español)";
        } else if (currentLangMode === "auto") {
            aiRoleLabel = "🤖 AI (Bilingual)";
        }

        if (this.chatMessages) {
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
            this.chatMessages.appendChild(aiBubble);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    updateUserTranslation(spanishText, turnId) {
        if (!spanishText) return;
        const el = document.getElementById(`user-tr-${turnId}`);
        if (el) {
            el.innerText = spanishText;
            el.classList.remove("translation-placeholder");
        }
    }

    appendAiChunk(delta, turnId) {
        const textEl = document.getElementById(`ai-text-${turnId}`);
        if (textEl) {
            textEl.innerText += delta;
            if (this.chatMessages) this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    updateAiTranslation(spanishText, turnId) {
        if (!spanishText) return;
        const container = document.getElementById(`ai-tr-${turnId}`);
        if (container) {
            const content = container.querySelector(".ai-translation-content");
            if (content) content.innerText = spanishText;
            container.classList.remove("hidden");
            if (this.chatMessages) this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    handleToolExecuted(data) {
        if (!this.chatMessages) return;
        const toolCard = document.createElement("div");
        toolCard.className = "tool-badge-card";
        const icon = data.tool === "get_current_time" ? "🕒" :
                     data.tool === "search_web" ? "🌐" :
                     data.tool === "launch_application" ? "🚀" :
                     data.tool === "get_hardware_status" ? "⚡" : "📝";

        toolCard.innerHTML = `
            <div class="tool-badge-header">
                <span class="tool-icon">${icon}</span>
                <span class="tool-name">${data.tool.replace(/_/g, " ").toUpperCase()}</span>
            </div>
            <div class="tool-badge-body">${this.escapeHtml(data.display_response || data.spoken_response)}</div>
        `;
        this.chatMessages.appendChild(toolCard);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showCoachingTip(tip) {
        if (!tip || !this.coachingContent) return;
        const box = document.createElement("div");
        box.className = "tip-box";
        box.innerHTML = `<strong>💡 Observación:</strong> ${this.escapeHtml(tip)}`;

        if (this.coachingContent.querySelector(".empty-tip")) {
            this.coachingContent.innerHTML = "";
        }
        this.coachingContent.prepend(box);
    }

    addToVocabulary(sentence) {
        if (!this.vocabularyList || !sentence) return;
        if (this.vocabularyList.querySelector(".empty-tip")) {
            this.vocabularyList.innerHTML = "";
        }
        const item = document.createElement("div");
        item.style.padding = "6px 0";
        item.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
        item.innerText = `• "${sentence}"`;
        this.vocabularyList.prepend(item);
    }

    exportSessionToMarkdown() {
        if (!this.chatMessages) return;
        const bubbles = this.chatMessages.querySelectorAll(".message-bubble:not(.partial)");
        if (bubbles.length === 0) {
            alert("No hay mensajes en la sesión actual para exportar.");
            return;
        }

        let md = `# 🎙️ Sesión de Conversación - Voice Assistant Local\n\n`;
        md += `*Fecha de Exportación:* ${new Date().toLocaleString()}\n`;
        md += `*Dispositivo:* NVIDIA RTX 4050 CUDA · 100% Offline\n\n---\n\n`;

        bubbles.forEach((b) => {
            const roleEl = b.querySelector(".bubble-role");
            const timeEl = b.querySelector(".bubble-time");
            const textEl = b.querySelector(".bubble-text-en");
            const trEl = b.querySelector(".bubble-text-es");

            const role = roleEl ? roleEl.innerText.trim() : "Mensaje";
            const time = timeEl ? timeEl.innerText.trim() : "";
            const text = textEl ? textEl.innerText.trim() : "";
            const translation = (trEl && !trEl.classList.contains("hidden")) ? trEl.innerText.replace("🇪🇸", "").trim() : "";

            md += `### ${role} (${time})\n\n`;
            md += `> ${text}\n\n`;
            if (translation && !translation.includes("Traduciendo")) {
                md += `*Traducción:* ${translation}\n\n`;
            }
        });

        const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `sesion_voz_${new Date().toISOString().slice(0, 10)}.md`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

window.ChatUIManager = ChatUIManager;
