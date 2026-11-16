"""
custom_tools/dev_quote.py - Custom Modular Tool: Developer & Tech Quotes
"""
import random

TOOL_NAME = "dev_quote"
AUTHOR = "Comunidad Open Source"
VERSION = "1.0.0"
DESCRIPTION = "Retorna frases célebres y humorísticas sobre programación y tecnología."

TRIGGERS = [
    "frase de programador", "frase de programación", "frase geek", "consejo de código",
    "programmer quote", "coding quote", "dev quote", "tech quote"
]

QUOTES_ES = [
    "La simplicidad es el prerrequisito para la confiabilidad. — Edsger Dijkstra.",
    "Primero resuelve el problema. Luego, escribe el código. — John Johnson.",
    "Hay dos formas de escribir código sin errores; solo la tercera funciona.",
    "Medir el progreso de programación por líneas de código es como medir la construcción de aviones por su peso. — Bill Gates."
]

QUOTES_EN = [
    "Simplicity is prerequisite for reliability. — Edsger Dijkstra.",
    "First, solve the problem. Then, write the code. — John Johnson.",
    "There are only two hard things in Computer Science: cache invalidation and naming things. — Phil Karlton.",
    "Make it work, make it right, make it fast. — Kent Beck."
]

def execute(user_text: str, lang: str = "es") -> str:
    if lang.startswith("es"):
        return random.choice(QUOTES_ES)
    return random.choice(QUOTES_EN)
