import re
from typing import Tuple

class SentenceChunker:
    """
    Algoritmo de segmentación temprana de oraciones para streaming continuo (Gapless Audio).
    Prioriza oraciones completas (. ! ? \n) y frases con sentido completo.
    Evita cortes prematuros en comas de 1 o 2 palabras (ej: 'Sí,') para que la voz no se frene.
    """

    @staticmethod
    def extract_ready_sentence(buffer: str) -> Tuple[str, str, bool]:
        """
        Analiza el buffer acumulado de tokens del LLM.
        Retorna (oración_lista_para_tts, buffer_restante, hay_oracion_lista).
        """
        words = buffer.strip().split()
        if not words:
            return "", buffer, False

        has_sentence_end = any(p in buffer for p in [".", "!", "?", "\n"])
        has_long_clause = any(p in buffer for p in [",", ";", ":"]) and len(words) >= 7

        # 1. Fin de oración canónico (. ! ? \n) con al menos 3 palabras
        if has_sentence_end and len(words) >= 3:
            parts = re.split(r'([.!?\n]+)', buffer)
            if len(parts) > 1:
                ready_sentence = (parts[0] + parts[1]).strip()
                remaining = "".join(parts[2:])
                return ready_sentence, remaining, True

        # 2. Cláusula larga separada por coma o dos puntos (mínimo 5 palabras antes de la coma)
        elif has_long_clause:
            parts = re.split(r'([,;:]+)', buffer)
            if len(parts) > 1 and len(parts[0].split()) >= 5:
                ready_sentence = (parts[0] + parts[1]).strip()
                remaining = "".join(parts[2:])
                return ready_sentence, remaining, True
            elif len(words) >= 11:
                ready_sentence = " ".join(words[:8]).strip()
                remaining = " ".join(words[8:]).strip()
                return ready_sentence, remaining, True

        # 3. Buffer saturado de palabras sin puntuación
        elif len(words) >= 12:
            ready_sentence = " ".join(words[:8]).strip()
            remaining = " ".join(words[8:]).strip()
            return ready_sentence, remaining, True

        return "", buffer, False
