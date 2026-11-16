import re
from typing import Tuple

class SentenceChunker:
    """
    Algoritmo de segmentación temprana de oraciones para streaming continuo (Gapless Audio).
    Prioriza oraciones completas (. ! ? \n) y frases con sentido completo.
    Incluye aceleración de sub-oraciones (Sub-Sentence Streaming) para el primer bloque
    (is_first_chunk=True) logrando latencias TTFA por debajo de 600 ms.
    """

    @staticmethod
    def extract_ready_sentence(buffer: str, is_first_chunk: bool = False) -> Tuple[str, str, bool]:
        """
        Analiza el buffer acumulado de tokens del LLM.
        Retorna (oración_lista_para_tts, buffer_restante, hay_oracion_lista).
        """
        words = buffer.strip().split()
        if not words:
            return "", buffer, False

        has_sentence_end = any(p in buffer for p in [".", "!", "?", "\n"])

        # 1. Fin de oración canónico (. ! ? \n)
        min_words_end = 2 if is_first_chunk else 3
        if has_sentence_end and len(words) >= min_words_end:
            parts = re.split(r'([.!?\n]+)', buffer)
            if len(parts) > 1:
                ready_sentence = (parts[0] + parts[1]).strip()
                remaining = "".join(parts[2:])
                return ready_sentence, remaining, True

        # 2. Cláusula temprana para el primer bloque (Sub-Sentence Streaming ultra-rápido)
        if is_first_chunk:
            has_clause_break = any(p in buffer for p in [",", ";", ":", "—"])
            if has_clause_break and len(words) >= 4:
                parts = re.split(r'([,;:—]+)', buffer)
                if len(parts) > 1 and len(parts[0].split()) >= 3:
                    ready_sentence = (parts[0] + parts[1]).strip()
                    remaining = "".join(parts[2:])
                    return ready_sentence, remaining, True
            elif len(words) >= 6:
                # Si el LLM no produce comas tempranas pero ya tenemos 5-6 palabras acumuladas
                ready_sentence = " ".join(words[:5]).strip() + ","
                remaining = " ".join(words[5:]).strip()
                return ready_sentence, remaining, True

        # 3. Cláusula normal para bloques subsecuentes (mínimo 5 palabras antes de la coma)
        has_long_clause = any(p in buffer for p in [",", ";", ":"]) and len(words) >= 7
        if has_long_clause:
            parts = re.split(r'([,;:]+)', buffer)
            if len(parts) > 1 and len(parts[0].split()) >= 5:
                ready_sentence = (parts[0] + parts[1]).strip()
                remaining = "".join(parts[2:])
                return ready_sentence, remaining, True
            elif len(words) >= 11:
                ready_sentence = " ".join(words[:8]).strip()
                remaining = " ".join(words[8:]).strip()
                return ready_sentence, remaining, True

        # 4. Buffer saturado de palabras sin puntuación
        elif len(words) >= 12:
            ready_sentence = " ".join(words[:8]).strip()
            remaining = " ".join(words[8:]).strip()
            return ready_sentence, remaining, True

        return "", buffer, False
