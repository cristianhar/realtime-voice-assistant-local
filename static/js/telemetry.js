// ==============================================================================
// Voice Assistant - GPU Telemetry Manager (NVIDIA RTX Live Hardware Polling)
// ==============================================================================

class GpuTelemetryManager {
    constructor(elements = {}) {
        this.pill = elements.pill || document.getElementById("gpu-telemetry-pill");
        this.label = elements.label || document.getElementById("gpu-telemetry-label");
        this.pollTimer = null;
    }

    startPolling(intervalMs = 4500) {
        this.fetchStatus();
        this.pollTimer = setInterval(() => this.fetchStatus(), intervalMs);
    }

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    async fetchStatus() {
        if (!this.pill || !this.label) return;
        try {
            const res = await fetch("/api/gpu-status");
            if (res.ok) {
                const data = await res.json();
                this.updateUI(data);
            }
        } catch (_) {}
    }

    updateUI(data) {
        if (!data || !data.available) {
            this.label.innerText = "GPU Fallback (CPU)";
            return;
        }

        const temp = data.temperature_c || 0;
        const used = data.memory_used_gb || 0;
        const total = data.memory_total_gb || 6.0;
        const pct = Math.round((used / total) * 100);

        this.label.innerText = `RTX 4050 • ${temp}°C • ${used}/${total}GB (${pct}%)`;

        this.pill.classList.remove("warm", "hot");
        if (temp >= 80) {
            this.pill.classList.add("hot");
        } else if (temp >= 70) {
            this.pill.classList.add("warm");
        }
    }
}

window.GpuTelemetryManager = GpuTelemetryManager;

