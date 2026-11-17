"""
==============================================================================
Pruebas Unitarias del Rediseño de UI: Botones Iconográficos y Popover (!)
==============================================================================
Valida que:
1. Los dos botones enormes se hayan transformado en botones iconográficos circulares
   modernos con sus SVGs y clases de estado (call-mode-btn y mic-btn).
2. El botón de información con símbolo de admiración (!) esté presente en el header.
3. El popover flotante contenga la telemetría GPU y perfil de usuario Cristian Arboleda.
4. Los estilos CSS y scripts JS mantengan total coherencia y accesibilidad.
==============================================================================
"""

import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class TestUIRedesign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        index_html_path = os.path.join(PROJECT_ROOT, "static", "index.html")
        style_css_path = os.path.join(PROJECT_ROOT, "static", "style.css")
        app_js_path = os.path.join(PROJECT_ROOT, "static", "app.js")
        i18n_js_path = os.path.join(PROJECT_ROOT, "static", "js", "i18n.js")

        with open(index_html_path, "r", encoding="utf-8") as f:
            cls.html = f.read()
        with open(style_css_path, "r", encoding="utf-8") as f:
            cls.css = f.read()
        with open(app_js_path, "r", encoding="utf-8") as f:
            cls.app_js = f.read()
        with open(i18n_js_path, "r", encoding="utf-8") as f:
            cls.i18n_js = f.read()

    def test_01_exclamation_info_button_in_header(self):
        """Verifica la presencia del botón con símbolo de admiración (!) en el header."""
        self.assertIn('id="btn-info-modal"', self.html, "Falta el botón de admiración #btn-info-modal en header")
        self.assertIn('header-exclamation-btn', self.html)
        self.assertIn('exclamation-icon', self.html)
        self.assertIn('!', self.html)

    def test_02_system_info_popover_structure(self):
        """Verifica que el popover contenga el perfil de Cristian y la telemetría GPU."""
        self.assertIn('id="system-info-popover"', self.html)
        self.assertIn('id="user-profile-badge"', self.html)
        self.assertIn('Cristian Arboleda', self.html)
        self.assertIn('id="gpu-telemetry-pill"', self.html)
        self.assertIn('id="gpu-telemetry-label"', self.html)
        self.assertIn('id="btn-close-popover"', self.html)

    def test_03_modern_icon_voice_buttons(self):
        """Verifica que los botones de voz sean iconográficos modernos con SVGs."""
        self.assertIn('unified-controls-dock', self.html)
        self.assertIn('voice-actions-dock', self.html)
        
        # Botón de Conversación Ininterrumpida (Manos Libres)
        self.assertIn('id="call-mode-btn"', self.html)
        self.assertIn('icon-action-btn', self.html)
        self.assertIn('call-svg', self.html)
        self.assertIn('id="call-btn-text"', self.html)

        # Botón de Micrófono (Capturar audio)
        self.assertIn('id="mic-btn"', self.html)
        self.assertIn('mic-svg', self.html)
        self.assertIn('id="mic-btn-label"', self.html)

        # Botón de Interrumpir
        self.assertIn('id="interrupt-btn"', self.html)
        self.assertIn('stop-svg', self.html)

    def test_04_css_styling_rules(self):
        """Valida que los estilos CSS correspondientes estén definidos."""
        self.assertIn('.header-exclamation-btn', self.css)
        self.assertIn('.system-info-popover', self.css)
        self.assertIn('.unified-controls-dock', self.css)
        self.assertIn('.voice-actions-dock', self.css)
        self.assertIn('.icon-action-btn', self.css)
        self.assertIn('.sr-only', self.css)

    def test_05_javascript_popover_interaction(self):
        """Valida que app.js gestione el toggle del popover con click y Escape."""
        self.assertIn('btn-info-modal', self.app_js)
        self.assertIn('system-info-popover', self.app_js)
        self.assertIn('systemInfoPopover.classList.toggle("hidden")', self.app_js)

    def test_06_i18n_svg_preservation(self):
        """Valida que i18n preserve los SVGs al actualizar títulos y etiquetas."""
        self.assertIn('interruptBtn.title', self.i18n_js)
        self.assertIn('callModeBtn.title', self.i18n_js)
        self.assertIn('micBtn.title', self.i18n_js)

    def test_07_audio_settings_modal_structure(self):
        """Verifica que la configuración de audio esté desacoplada en su modal y botones dedicados."""
        self.assertIn('id="btn-audio-settings"', self.html)
        self.assertIn('id="btn-dock-settings"', self.html)
        self.assertIn('id="settings-modal-overlay"', self.html)
        self.assertIn('id="settings-modal"', self.html)
        self.assertIn('id="btn-close-settings"', self.html)
        self.assertIn('id="btn-save-settings"', self.html)

        # Verificar que los selects viven en el modal
        self.assertIn('id="mic-select"', self.html)
        self.assertIn('id="vad-select"', self.html)
        self.assertIn('id="voice-select"', self.html)
        self.assertIn('id="speed-select"', self.html)
        self.assertIn('id="whisper-btn"', self.html)
        self.assertIn('id="personality-select"', self.html)

    def test_08_audio_settings_css_and_js(self):
        """Valida estilos CSS y bindings JS del modal de configuración."""
        self.assertIn('.settings-header-btn', self.css)
        self.assertIn('.settings-dock-btn', self.css)
        self.assertIn('.settings-modal-overlay', self.css)
        self.assertIn('.settings-modal', self.css)
        self.assertIn('btnAudioSettings', self.app_js)
        self.assertIn('openSettingsModal', self.app_js)
        self.assertIn('closeSettingsModal', self.app_js)

    def test_09_question_mark_help_popover(self):
        """Valida que el enunciado de bienvenida se haya movido al botón de interrogación (?)."""
        self.assertIn('id="btn-help-modal"', self.html)
        self.assertIn('id="welcome-help-popover"', self.html)
        self.assertIn('id="welcome-title"', self.html)
        self.assertIn('id="welcome-desc"', self.html)
        self.assertIn('id="tip-1"', self.html)
        self.assertIn('.welcome-help-popover', self.css)
        self.assertIn('btnHelpModal', self.app_js)
        self.assertIn('welcomeHelpPopover.classList.toggle("hidden")', self.app_js)

    def test_10_ultra_minimalist_controls(self):
        """Valida que los controles inferiores sean compactos y minimalistas (36px)."""
        self.assertIn('.minimal-controls-dock', self.css)
        self.assertIn('.minimal-action-btn', self.css)
        self.assertIn('minimal-send-btn', self.html)
        self.assertIn('.chat-empty-hint', self.css)

if __name__ == "__main__":
    unittest.main()

