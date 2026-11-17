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
        clean_buf = buffer.lstrip('\r\n\t ')
        words = clean_buf.split()
        if not words:
            return "", buffer, False

        # 1. Fin de oración canónico (. ! ? \n)
        # Evitar cortar en puntos decimales (ej. 3.14 o 3.2B) usando lookaround numérico
        pattern = r'((?:(?<!\d)[.!?]+(?!\d)|[\r\n]+))'
        parts = re.split(pattern, clean_buf)
        if len(parts) > 1 and parts[0].strip():
            ready_sentence = (parts[0] + parts[1]).strip()
            remaining = "".join(parts[2:])
            return ready_sentence, remaining, True

        # 2. Cláusula sintáctica con signo de pausa (, ; : —)
        clause_pattern = r'([,;:—]+)'
        if any(p in clean_buf for p in [",", ";", ":", "—"]):
            c_parts = re.split(clause_pattern, clean_buf)
            min_clause = 4 if is_first_chunk else 5
            if len(c_parts) > 1 and len(c_parts[0].split()) >= min_clause:
                ready_sentence = (c_parts[0] + c_parts[1]).strip()
                remaining = "".join(c_parts[2:])
                return ready_sentence, remaining, True

        # 3. Buffer desbordado de palabras continuas sin ninguna puntuación
        elif len(words) >= 13:
            ready_sentence = " ".join(words[:8]).strip()
            remaining = " ".join(words[8:]).strip()
            return ready_sentence, remaining, True

        return "", buffer, False
