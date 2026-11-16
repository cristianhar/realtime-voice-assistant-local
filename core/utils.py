import sys
import re

def configure_utf8_stdio():
    """Garantiza codificación UTF-8 en stdout y stderr para consolas Windows y CI."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

SPANISH_CHARS = set("áéíóúüñ¿¡")
COMMON_SPANISH_WORDS = {
    "hola", "cómo", "como", "estás", "estas", "qué", "que", "buenos", "días",
    "gracias", "por", "favor", "sí", "si", "no", "bien", "amigo", "para", "pero",
    "buenas", "tardes", "noches", "claro", "mucho", "gusto", "ayuda", "puedo", "hacer", "estoy",
    "tienes", "tengo", "quiero", "dónde", "donde", "cuándo", "cuando", "porqué", "porque"
}

def is_text_spanish(text: str) -> bool:
    """Heurística rápida para detectar si un texto corto es español o inglés."""
    if not text:
        return False
    lower = text.lower()
    if any(c in SPANISH_CHARS for c in lower):
        return True
    words = set(re.findall(r'\b\w+\b', lower))
    return len(words.intersection(COMMON_SPANISH_WORDS)) > 0

CONVERSATIONAL_FILLERS = {
    "es": {
        "thinking": ["Mmm...", "A ver...", "Veamos..."],
        "agreement": ["Claro...", "Por supuesto...", "Entendido..."],
        "searching": ["Un segundo...", "Déjame revisar...", "Buscando..."]
    },
    "en": {
        "thinking": ["Mmm...", "Let's see...", "Well..."],
        "agreement": ["Sure...", "Got it...", "Right..."],
        "searching": ["One second...", "Let me check...", "Looking that up..."]
    }
}

def get_conversational_filler(lang: str = "es", intent: str = "thinking") -> str:
    """Retorna un filler orgánico contextual para simular pausas cognitivas humanas."""
    lang_key = "es" if lang.startswith("es") else "en"
    intent_key = intent if intent in CONVERSATIONAL_FILLERS[lang_key] else "thinking"
    options = CONVERSATIONAL_FILLERS[lang_key][intent_key]
    import random
    return random.choice(options)


