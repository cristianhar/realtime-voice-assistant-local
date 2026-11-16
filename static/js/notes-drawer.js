// ==============================================================================
// Voice Assistant - Notes Drawer Manager (CRUD, Live Search & AI Synthesis)
// ==============================================================================

class NotesDrawerManager {
    constructor(elements = {}) {
        this.btnOpen = elements.btnOpen || document.getElementById("btn-open-notes-drawer");
        this.btnClose = elements.btnClose || document.getElementById("btn-close-notes-drawer");
        this.overlay = elements.overlay || document.getElementById("notes-drawer-overlay");
        this.drawer = elements.drawer || document.getElementById("notes-drawer");
        this.cardsContainer = elements.cardsContainer || document.getElementById("notes-cards-container");
        this.counterBadge = elements.counterBadge || document.getElementById("header-notes-counter");
        this.searchInput = elements.searchInput || document.getElementById("notes-search-input");
        this.btnSynthesize = elements.btnSynthesize || document.getElementById("btn-synthesize-notes");
        this.btnExport = elements.btnExport || document.getElementById("btn-export-notes-md");
        this.summaryCard = elements.summaryCard || document.getElementById("notes-ai-summary-card");
        this.summaryBody = elements.summaryBody || document.getElementById("notes-ai-summary-content");
        this.btnCloseSummary = elements.btnCloseSummary || document.getElementById("btn-close-summary");
        this.sideNotesList = elements.sideNotesList || document.getElementById("notes-list");

        this.notes = [];
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

        if (this.btnCloseSummary && this.summaryCard) {
            this.btnCloseSummary.addEventListener("click", () => {
                this.summaryCard.style.display = "none";
            });
        }

        if (this.searchInput) {
            this.searchInput.addEventListener("input", () => this.render());
        }

        if (this.btnSynthesize) {
            this.btnSynthesize.addEventListener("click", () => this.synthesizeWithAi());
        }

        if (this.btnExport) {
            this.btnExport.addEventListener("click", () => this.exportMarkdown());
        }
    }

    open() {
        if (this.drawer && this.overlay) {
            this.drawer.classList.add("open");
            this.overlay.classList.add("active");
            this.render();
        }
    }

    close() {
        if (this.drawer && this.overlay) {
            this.drawer.classList.remove("open");
            this.overlay.classList.remove("active");
        }
    }

    async fetchNotes() {
        try {
            const res = await fetch("/api/notes?limit=50");
            if (res.ok) {
                this.notes = await res.json() || [];
                if (this.counterBadge) {
                    this.counterBadge.innerText = this.notes.length.toString();
                }
                this.renderSideCard();
                if (this.drawer && this.drawer.classList.contains("open")) {
                    this.render();
                }
            }
        } catch (e) {
            console.warn("[NotesDrawer] Error cargando notas:", e);
        }
    }

    renderSideCard() {
        if (!this.sideNotesList) return;
        if (this.notes && this.notes.length > 0) {
            this.sideNotesList.innerHTML = "";
            this.notes.slice(0, 10).forEach(n => {
                const div = document.createElement("div");
                div.className = "note-item";
                div.innerHTML = `<strong>${this.escapeHtml(n.title)}</strong><span>${this.escapeHtml(n.content)}</span>`;
                this.sideNotesList.appendChild(div);
            });
        } else {
            this.sideNotesList.innerHTML = '<div class="empty-tip">No hay notas guardadas todavía. Di: "Toma nota de..."</div>';
        }
    }

    render() {
        if (!this.cardsContainer) return;
        const q = (this.searchInput ? this.searchInput.value.toLowerCase().trim() : "");
        const filtered = this.notes.filter(n =>
            (n.title && n.title.toLowerCase().includes(q)) ||
            (n.content && n.content.toLowerCase().includes(q))
        );

        if (!filtered || filtered.length === 0) {
            this.cardsContainer.innerHTML = '<div class="empty-tip" style="padding: 30px; text-align: center;">No hay notas que coincidan.</div>';
            return;
        }

        this.cardsContainer.innerHTML = "";
        filtered.forEach(n => {
            const card = document.createElement("div");
            card.className = "note-item-card";
            card.innerHTML = `
                <div class="note-card-header">
                    <h4 class="note-card-title">${this.escapeHtml(n.title)}</h4>
                    <button class="note-delete-btn" data-id="${n.id}" title="Eliminar nota">🗑️</button>
                </div>
                <div class="note-card-content">${this.escapeHtml(n.content)}</div>
                <div class="note-card-date">${this.escapeHtml(n.created_at || "")}</div>
            `;
            this.cardsContainer.appendChild(card);
        });

        this.cardsContainer.querySelectorAll(".note-delete-btn").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                e.stopPropagation();
                const noteId = btn.getAttribute("data-id");
                if (confirm("¿Deseas eliminar esta nota de voz?")) {
                    await this.deleteNote(noteId);
                }
            });
        });
    }

    async deleteNote(noteId) {
        try {
            const res = await fetch(`/api/notes/${noteId}`, { method: "DELETE" });
            if (res.ok) {
                this.notes = this.notes.filter(n => n.id != noteId);
                if (this.counterBadge) {
                    this.counterBadge.innerText = this.notes.length.toString();
                }
                this.render();
                this.renderSideCard();
            }
        } catch (e) {
            console.error("[NotesDrawer] Error eliminando nota:", e);
        }
    }

    async synthesizeWithAi() {
        if (this.notes.length === 0) {
            alert("No tienes notas guardadas para sintetizar.");
            return;
        }

        if (this.btnSynthesize) {
            this.btnSynthesize.disabled = true;
            this.btnSynthesize.innerText = "⏳ Sintetizando con LLaMA...";
        }

        try {
            const res = await fetch("/api/notes/synthesize", { method: "POST" });
            if (res.ok) {
                const data = await res.json();
                if (this.summaryCard && this.summaryBody) {
                    this.summaryBody.innerText = data.summary || "Sin resumen disponible.";
                    this.summaryCard.style.display = "block";
                }
            }
        } catch (e) {
            alert("Error al contactar con el modelo de síntesis.");
        } finally {
            if (this.btnSynthesize) {
                this.btnSynthesize.disabled = false;
                this.btnSynthesize.innerHTML = "<span>✨ Sintetizar con IA</span>";
            }
        }
    }

    exportMarkdown() {
        if (this.notes.length === 0) {
            alert("No hay notas para exportar.");
            return;
        }
        let md = `# 📝 Mis Notas de Voz - Voice Assistant\n\n`;
        md += `*Fecha de Exportación:* ${new Date().toLocaleString()}\n\n---\n\n`;
        this.notes.forEach((n, idx) => {
            md += `### ${idx + 1}. ${n.title}\n`;
            md += `*Fecha:* ${n.created_at || "N/A"}\n\n`;
            md += `${n.content}\n\n`;
        });

        const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `notas_voz_${new Date().toISOString().slice(0, 10)}.md`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

window.NotesDrawerManager = NotesDrawerManager;

