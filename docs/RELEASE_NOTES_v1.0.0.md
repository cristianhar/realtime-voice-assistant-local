# 🚀 Release Notes: Realtime Voice Assistant Local v1.0.0

We are thrilled to announce the official **v1.0.0** release of **Realtime Voice Assistant Local**, a full-duplex, 100% private and offline conversational AI engineered to run entirely on consumer hardware with 6GB VRAM GPUs.

---

## 🌟 Key Highlights

- **⚡ Sub-50ms Barge-In Interruption**: Talk over the assistant naturally mid-speech. Audio output is silenced in <0.02ms with immediate buffer cancellation.
- **🎙️ Natural Voice Humanization**: Organic cognitive pauses, Spanish and English conversational fillers (*"A ver..."*, *"Bueno..."*, *"Well..."*), and subtle pre-speech inhalation acoustics.
- **🧠 Spectral Formant VAD**: Multi-band FFT filtering that distinguishes voiced human vocal formants from mechanical keyboard typing and microphone breath puffs.
- **🧩 Custom Tools Engine (`custom_tools/`)**: Drop-in Python plugin architecture to add voice tools with zero boilerplate.
- **🎭 Persona Hub (`personas/`)**: Ready-to-use characters including J.A.R.V.I.S., Sarah (Language Coach), Alex (Tech Lead), and Aura (Zen Mindfulness).
- **📦 Agensi.io Certified Skills**: 3 packaged, verified Agent Skills for Claude Code, Cursor, Copilot, and Agensi marketplace.
- **💻 1-Click Installers**: Single-line automated setup via PowerShell (`install.ps1`) and Bash (`install.sh`).
- **🛡️ 100% Quality Gate**: Complete end-to-end testing suite with 76 passing tests running on GitHub Actions CI.

---

## 📥 Getting Started

### Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/cristianhar/realtime-voice-assistant-local/main/install.ps1 | iex
```

### Linux / macOS:
```bash
curl -fsSL https://raw.githubusercontent.com/cristianhar/realtime-voice-assistant-local/main/install.sh | bash
```

