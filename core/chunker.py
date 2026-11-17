import re
from typing import Tuple

class SentenceChunker:
    """
    Algoritmo de segmentación temprana de oraciones para streaming continuo (Gapless Audio).
    Prioriza oraciones completas (. ! ? \n) y cláusulas con sentido completo (, ; : —).
    Evita tajantemente cortar en palabras sueltas sin puntuación salvo desbordamiento extremo.
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

        # 1. Fin de oración canónico (. ! ? \n)
        has_sentence_end = any(p in buffer for p in [".", "!", "?", "\n"])
        min_words_end = 2 if is_first_chunk else 3
        if has_sentence_end and len(words) >= min_words_end:
            parts = re.split(r'([.!?\n]+)', buffer)
            if len(parts) > 1:
                ready_sentence = (parts[0] + parts[1]).strip()
                remaining = "".join(parts[2:])
                return ready_sentence, remaining, True

        # 2. Cláusula sintáctica con signo de pausa (, ; : —)
        has_clause_break = any(p in buffer for p in [",", ";", ":", "—"])
        if has_clause_break:
            parts = re.split(r'([,;:—]+)', buffer)
            min_clause = 4 if is_first_chunk else 5
            if len(parts) > 1 and len(parts[0].split()) >= min_clause:
                ready_sentence = (parts[0] + parts[1]).strip()
                remaining = "".join(parts[2:])
                return ready_sentence, remaining, True

        # 3. Buffer desbordado de palabras continuas sin ninguna puntuación
        elif len(words) >= 12:
            ready_sentence = " ".join(words[:8]).strip()
            remaining = " ".join(words[8:]).strip()
            return ready_sentence, remaining, True

        return "", buffer, False
