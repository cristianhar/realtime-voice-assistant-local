import time
import io
import wave
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.chunker import SentenceChunker

text = "Es un tema muy interesante, especialmente con la Inteligencia Artificial que estamos trabajando en actualmente. ¿Qué te parece si hablamos de ello?"
tokens = text.split()

print("=" * 65)
print("  CRONOGRAMA DE SINCRONIZACIÓN REAL (TEXTO vs AUDIO vs ESTADO)")
print("=" * 65)

buffer = ""
is_first = True
chunks = []
for t in tokens:
    buffer += (" " if buffer else "") + t
    s, r, ok = SentenceChunker.extract_ready_sentence(buffer, is_first_chunk=is_first)
    if ok:
        chunks.append(s)
        buffer = r
        is_first = False
if buffer.strip():
    chunks.append(buffer.strip())

llm_elapsed = 0.0
events = []

for i, chunk in enumerate(chunks):
    word_count = len(chunk.split())
    # Locución en español: ~2.5 palabras/segundo
    audio_dur = word_count / 2.5
    # Tiempo de streaming de tokens en Ollama (~35ms por token/palabra)
    token_time = word_count * 0.035
    llm_elapsed += token_time
    # Tiempo de síntesis multihilo de Kokoro en CPU (~400ms)
    tts_synth_time = 0.40
    chunk_arrives_at = llm_elapsed + tts_synth_time

    events.append({
        "id": i,
        "text": chunk,
        "words": word_count,
        "audio_dur": audio_dur,
        "arrives_at": chunk_arrives_at
    })

print("\n1. GENERACIÓN EN SERVIDOR (Streaming de Chunks):")
for e in events:
    print(f"   [Chunk {e['id']}] \"{e['text']}\"")
    print(f"      Palabras: {e['words']} | Audio generado: {e['audio_dur']:.2f}s | Llega al cliente en: t={e['arrives_at']:.2f}s")

print(f"\n   -> Fin total de generación de texto LLM: t={llm_elapsed:.2f}s")
print(f"   -> El servidor envía evento 'ai_done':    t={events[-1]['arrives_at']:.2f}s")

print("\n2. REPRODUCCIÓN EN CLIENTE (AudioPlayerManager en navegador):")
t_play = events[0]["arrives_at"]
print(f"   [t={t_play:.2f}s] Orbe cambia a 'HABLANDO...' -> Empieza a sonar Chunk 0")

for i, e in enumerate(events):
    start_play = t_play
    end_play = t_play + e["audio_dur"]
    next_ready = events[i + 1]["arrives_at"] if i + 1 < len(events) else None

    status = "CONTINUO (En cola antes de terminar)"
    if next_ready:
        margin = end_play - next_ready
        status = f"CONTINUO (Llega {margin:.2f}s ANTES de que termine este)"

    print(f"   🔊 Sonando Chunk {i}: de t={start_play:.2f}s a t={end_play:.2f}s | {status}")
    t_play = end_play

print(f"\n3. MOMENTO ESPERADO DE FIN:")
print(f"   [t={t_play:.2f}s] El último milisegundo de audio termina de sonar en tus auriculares.")
print(f"   [t={t_play:.2f}s] AudioPlayerManager.finalizeTurn() dispara onPlayEnd().")
print(f"   [t={t_play:.2f}s] El orbe pasa a 'Listo para conversar' (IDLE) exactamente en el momento justo.")
print("=" * 65)
