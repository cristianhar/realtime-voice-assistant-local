import re

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

