// ==============================================================================
// Voice Assistant - Conversation History Drawer (ChatGPT Style)
// ==============================================================================

class HistoryDrawerManager {
    constructor(elements = {}, options = {}) {
        this.btnOpen = elements.btnOpen || document.getElementById("btn-open-history-drawer");
        this.btnClose = elements.btnClose || document.getElementById("btn-close-history-drawer");
        this.overlay = elements.overlay || document.getElementById("history-drawer-overlay");
        this.drawer = elements.drawer || document.getElementById("history-drawer");
        this.cardsContainer = elements.cardsContainer || document.getElementById("history-cards-container");
        this.counterBadge = elements.counterBadge || document.getElementById("header-history-counter");
        this.searchInput = elements.searchInput || document.getElementById("history-search-input");
        this.btnNewChat = elements.btnNewChat || document.getElementById("btn-new-chat-drawer");

        this.onSwitchSession = options.onSwitchSession || null;
        this.onNewChat = options.onNewChat || null;

        this.sessions = [];
        this.activeSessionId = options.initialSessionId || null;
        this.initEventListeners();
    }

    escapeHtml(text) {
        const div = document.createElement("div");
        div.innerText = text;
        return div.innerHTML;
    }

    initEventListeners() {
        if (this.btnOpen) this.btnOpen.addEventListener("click", () => this.open());
        if (this.btnClose) this.btnClose.addEventListener("click", () => this.close());
        if (this.overlay) this.overlay.addEventListener("click", () => this.close());

        if (this.searchInput) {
            this.searchInput.addEventListener("input", () => this.render());
        }

        if (this.btnNewChat) {
            this.btnNewChat.addEventListener("click", () => this.createNewSession());
        }

        // Tecla Escape para cerrar
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && this.drawer && this.drawer.classList.contains("open")) {
                this.close();
            }
        });
    }

    open() {
        if (this.drawer && this.overlay) {
            this.drawer.classList.add("open");
            this.overlay.classList.add("active");
            this.fetchSessions();
        }
    }

    close() {
        if (this.drawer && this.overlay) {
            this.drawer.classList.remove("open");
            this.overlay.classList.remove("active");
        }
    }

    async fetchSessions() {
        try {
            const res = await fetch("/api/sessions");
            if (res.ok) {
                const data = await res.json();
                this.sessions = data.sessions || [];
                if (this.counterBadge) {
                    this.counterBadge.innerText = this.sessions.length.toString();
                }
                this.render();
            }
        } catch (e) {
            console.error("[HistoryDrawer] Error cargando sesiones:", e);
        }
    }

    setActiveSession(sessionId) {
        this.activeSessionId = sessionId;
        this.render();
    }

    onTitleGenerated(sessionId, newTitle) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            session.title = newTitle;
            this.render();
        } else {
            this.fetchSessions();
        }
    }

    async createNewSession() {
        try {
            const res = await fetch("/api/sessions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: "Nueva conversación" })
            });
            if (res.ok) {
                const data = await res.json();
                const newId = data.session_id;
                this.activeSessionId = newId;
                await this.fetchSessions();
                this.close();
                if (typeof this.onNewChat === "function") {
                    this.onNewChat(newId, data.title);
                }
            }
        } catch (e) {
            console.error("[HistoryDrawer] Error creando nueva conversación:", e);
        }
    }

    async selectSession(sessionId) {
        this.activeSessionId = sessionId;
        this.render();
        this.close();

        try {
            const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/messages`);
            if (res.ok) {
                const data = await res.json();
                if (typeof this.onSwitchSession === "function") {
                    this.onSwitchSession(sessionId, data.messages || []);
                }
            }
        } catch (e) {
            console.error(`[HistoryDrawer] Error cargando mensajes de ${sessionId}:`, e);
        }
    }

    async renameSession(sessionId, currentTitle) {
        const newTitle = prompt("Escribe el nuevo título para esta conversación:", currentTitle);
        if (!newTitle || !newTitle.trim() || newTitle.trim() === currentTitle) return;

        try {
            const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/title`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: newTitle.trim() })
            });
            if (res.ok) {
                const session = this.sessions.find(s => s.id === sessionId);
                if (session) session.title = newTitle.trim();
                this.render();
            }
        } catch (e) {
            console.error(`[HistoryDrawer] Error renombrando ${sessionId}:`, e);
        }
    }

    async generateAiTitle(sessionId, btnElement) {
        if (btnElement) {
            btnElement.disabled = true;
            btnElement.classList.add("loading");
            btnElement.innerText = "⏳";
        }
        try {
            const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/generate-title`, {
                method: "POST"
            });
            if (res.ok) {
                const data = await res.json();
                const session = this.sessions.find(s => s.id === sessionId);
                if (session && data.title) {
                    session.title = data.title;
                    this.render();
                }
            }
        } catch (e) {
            console.error(`[HistoryDrawer] Error generando título IA para ${sessionId}:`, e);
        } finally {
            if (btnElement) {
                btnElement.disabled = false;
                btnElement.classList.remove("loading");
                btnElement.innerText = "🤖";
            }
        }
    }

    async deleteSession(sessionId, title) {
        const confirmMsg = `¿Eliminar la conversación "${title || 'esta conversación'}"?\nSe borrarán todos sus mensajes de forma permanente.`;
        if (!confirm(confirmMsg)) return;

        try {
            const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
                method: "DELETE"
            });
            if (res.ok) {
                this.sessions = this.sessions.filter(s => s.id !== sessionId);
                if (this.counterBadge) {
                    this.counterBadge.innerText = this.sessions.length.toString();
                }
                this.render();

                // Si eliminamos la sesión que estaba activa, iniciar nueva conversación
                if (this.activeSessionId === sessionId) {
                    this.createNewSession();
                }
            }
        } catch (e) {
            console.error(`[HistoryDrawer] Error eliminando ${sessionId}:`, e);
        }
    }

    render() {
        if (!this.cardsContainer) return;

        const query = (this.searchInput ? this.searchInput.value : "").trim().toLowerCase();
        const filtered = this.sessions.filter(s => {
            const title = (s.title || "").toLowerCase();
            return !query || title.includes(query) || (s.id && s.id.toLowerCase().includes(query));
        });

        if (filtered.length === 0) {
            this.cardsContainer.innerHTML = `
                <div class="history-empty">
                    <span>💬</span>
                    <p>${query ? "No se encontraron conversaciones con ese filtro." : "Aún no tienes conversaciones guardadas. ¡Habla o escribe para comenzar!"}</p>
                </div>
            `;
            return;
        }

        let html = "";
        filtered.forEach(s => {
            const isActive = s.id === this.activeSessionId;
            const dateStr = s.updated_at || s.created_at || "";
            const displayDate = dateStr ? new Date(dateStr).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : "";
            const turnsCount = s.total_turns || 0;
            const titleSafe = this.escapeHtml(s.title || "Nueva conversación");

            html += `
                <div class="history-item ${isActive ? 'active' : ''}" data-id="${s.id}">
                    <div class="history-item-content" onclick="window.historyDrawer.selectSession('${s.id}')">
                        <div class="history-item-header">
                            <span class="history-item-icon">💬</span>
                            <span class="history-item-title" title="${titleSafe}">${titleSafe}</span>
                        </div>
                        <div class="history-item-meta">
                            <span>${displayDate}</span>
                            <span>•</span>
                            <span>${turnsCount} mensajes</span>
                        </div>
                    </div>
                    <div class="history-item-actions">
                        <button class="history-action-btn edit-btn" title="Renombrar conversación" onclick="event.stopPropagation(); window.historyDrawer.renameSession('${s.id}', '${s.title || 'Nueva conversación'}')">
                            ✏️
                        </button>
                        <button class="history-action-btn ai-btn" title="Generar título con IA (LLaMA 3.2)" onclick="event.stopPropagation(); window.historyDrawer.generateAiTitle('${s.id}', this)">
                            🤖
                        </button>
                        <button class="history-action-btn delete-btn" title="Eliminar conversación" onclick="event.stopPropagation(); window.historyDrawer.deleteSession('${s.id}', '${s.title || 'Nueva conversación'}')">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        });

        this.cardsContainer.innerHTML = html;
    }
}

window.HistoryDrawerManager = HistoryDrawerManager;

