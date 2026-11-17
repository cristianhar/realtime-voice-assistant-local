"""
custom_tools/dice_roller.py - Custom Modular Tool: Dice & Coin Randomizer
Demonstrates how easy it is to create modular voice tools.
"""
import random
import re

TOOL_NAME = "dice_roller"
AUTHOR = "Cristian Arboleda"
VERSION = "1.0.0"
DESCRIPTION = "Lanza dados virtuales (D6, D20) o monedas con respuesta de voz natural."

TRIGGERS = [
    "tira un dado", "tirar dado", "lanza un dado", "lanzar dado",
    "roll a die", "roll a dice", "roll dice",
    "tira una moneda", "lanza una moneda", "cara o cruz",
    "flip a coin", "coin flip", "heads or tails"
]

def execute(user_text: str, lang: str = "es") -> str:
    lower = user_text.lower()
    is_coin = any(k in lower for k in ["moneda", "coin", "cara o cruz", "heads or tails"])

    if is_coin:
        side = random.choice(["cara", "cruz"] if lang.startswith("es") else ["heads", "tails"])
        if lang.startswith("es"):
            return f"Lanzando la moneda... ¡Cayó {side}!"
        return f"Flipping the coin... It landed on {side}!"

    # Dice roll (check if D20, D100, or default D6)
    sides = 6
    match = re.search(r'd(20|100|12|10|8|4)', lower)
    if match:
        sides = int(match.group(1))

    val = random.randint(1, sides)
    if lang.startswith("es"):
        return f"Tirando un dado de {sides} caras... ¡Salió {val}!"
    return f"Rolling a {sides}-sided die... You got a {val}!"

