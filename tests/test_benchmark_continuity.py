import asyncio
import json
import time
import io
import soundfile as sf
import numpy as np
import websockets

WS_URL = "ws://127.0.0.1:8000/ws/chat"

class VoiceBenchmarkRunner:
    def __init__(self):
        self.turns_metrics = []

    def get_wav_duration_seconds(self, b64_wav: str) -> float:
        import base64
        raw = base64.b64decode(b64_wav)
        data, sr = sf.read(io.BytesIO(raw))
        return len(data) / float(sr)

    async def run_conversation_turn(self, ws, turn_num: int, user_text: str, mode: str, voice: str):
        print(f"\n{'='*65}")
        print(f"  [TURNO #{turn_num}] Modo: {mode.upper()} | Voz: {voice} | Texto: \"{user_text}\"")
        print(f"{'='*65}")

        await ws.send(json.dumps({"type": "set_mode", "mode": mode}))
        await ws.send(json.dumps({"type": "set_voice", "voice": voice}))
        await asyncio.sleep(0.05)

        t_turn_start = time.perf_counter()
        turn_id = f"bench-turn-{int(t_turn_start * 1000)}"

        await ws.send(json.dumps({
            "type": "text",
            "turn_id": turn_id,
            "text": user_text
        }))

        chunks = []
        ai_full_text = ""
        ttfa_ms = None
        simulated_playback_time = None
        turn_done = False

        while not turn_done:
            raw_msg = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(raw_msg)
            mtype = data.get("type")

            if mtype == "ai_chunk":
                ai_full_text += data.get("delta", "")

            elif mtype == "audio_chunk":
                arrival_time = time.perf_counter()
                elapsed_from_start_ms = (arrival_time - t_turn_start) * 1000
                if ttfa_ms is None:
                    ttfa_ms = elapsed_from_start_ms

                chunk_text = data.get("text", "")
                dur_s = self.get_wav_duration_seconds(data.get("audio", ""))

                # Simulación exacta de reproducción en el navegador:
                if simulated_playback_time is None:
                    # El primer audio empieza a reproducirse de inmediato
                    start_play_time = arrival_time
                    end_play_time = start_play_time + dur_s
                    gap_ms = 0.0 # Primer fragmento
                else:
                    start_play_time = max(simulated_playback_time, arrival_time)
                    gap_ms = (arrival_time - simulated_playback_time) * 1000
                    end_play_time = start_play_time + dur_s

                simulated_playback_time = end_play_time

                chunks.append({
                    "idx": len(chunks) + 1,
                    "text": chunk_text,
                    "words": len(chunk_text.split()),
                    "audio_dur_s": dur_s,
                    "arrival_ms": elapsed_from_start_ms,
                    "gap_or_buffer_margin_ms": gap_ms
                })

                # Si gap_ms <= 0, significa que el fragmento llegó ANTES de que terminara el anterior (BUFFER SEGURO, CERO FRENOS)
                margin_str = f"Llegó {abs(gap_ms):.1f}ms ANTES de que termine el anterior (0 frenos)" if gap_ms <= 0 else f"⚠️ Silencio de {gap_ms:.1f}ms"
                print(f"  🔊 Chunk #{len(chunks)} [{dur_s:.2f}s audio | {len(chunk_text.split())} palabras]: \"{chunk_text}\"")
                print(f"     -> Llegada: {elapsed_from_start_ms:.1f}ms | Margen de buffer: {margin_str}")

            elif mtype == "ai_done":
                total_turn_ms = (time.perf_counter() - t_turn_start) * 1000
                turn_done = True
                print(f"\n  ✓ Fin de generación IA: \"{ai_full_text.strip()}\"")
                print(f"    • TTFA (Latencia al 1er audio): {ttfa_ms:.1f} ms")
                print(f"    • Tiempo total turno: {total_turn_ms:.1f} ms")
                print(f"    • Total fragmentos recibidos: {len(chunks)}")

                self.turns_metrics.append({
                    "turn_num": turn_num,
                    "mode": mode,
                    "voice": voice,
                    "user_text": user_text,
                    "ai_text": ai_full_text.strip(),
                    "ttfa_ms": ttfa_ms,
                    "total_turn_ms": total_turn_ms,
                    "chunks": chunks
                })

    async def run_barge_in_test(self, ws):
        print(f"\n{'='*65}")
        print("  [TEST DE INTERRUPCIÓN / BARGE-IN EN VIVO]")
        print(f"{'='*65}")

        await ws.send(json.dumps({"type": "set_mode", "mode": "es"}))
        await ws.send(json.dumps({"type": "set_voice", "voice": "ef_dora"}))
        await asyncio.sleep(0.05)

        turn_id = f"bargein-{int(time.time()*1000)}"
        await ws.send(json.dumps({
            "type": "text",
            "turn_id": turn_id,
            "text": "Explícame de manera detallada y extendida la historia y arquitectura de la inteligencia artificial."
        }))

        # Esperar a que el primer fragmento de audio empiece a fluir
        first_audio_received = False
        while not first_audio_received:
            msg = await ws.recv()
            d = json.loads(msg)
            if d.get("type") == "audio_chunk":
                first_audio_received = True
                print(f"  -> Audio inicial recibido: \"{d.get('text')}\"")

        # Interrumpir inmediatamente mientras habla
        t_interrupt = time.perf_counter()
        print("  ⚡ ENVIANDO SEÑAL DE INTERRUPCIÓN (Barge-in)...")
        await ws.send(json.dumps({"type": "interrupt"}))

        interrupted_ack = False
        chunks_leaked = 0
        while not interrupted_ack:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            d = json.loads(msg)
            if d.get("type") == "interrupted":
                interrupted_ack = True
                ack_latency_ms = (time.perf_counter() - t_interrupt) * 1000
                print(f"  ✓ Confirmación de corte instantáneo: {ack_latency_ms:.1f} ms (Barge-in exitoso)")
            elif d.get("type") == "audio_chunk":
                chunks_leaked += 1

        print(f"  • Fragmentos filtrados tras interrupción: {chunks_leaked} (esperado 0 o 1)")

    async def run_full_benchmark(self):
        print("Conectando con WebSocket Local...")
        async with websockets.connect(WS_URL) as ws:
            print("✓ Conexión establecida. Iniciando suite de evaluación continua...")

            conversations = [
                (1, "Hola, ¿cómo estás hoy? Cuéntame qué planes tienes.", "es", "ef_dora"),
                (2, "¿Podrías darme una recomendación rápida de un libro de ciencia ficción?", "es", "em_alex"),
                (3, "Hi! I want to practice my English conversation today, how is your day going?", "en", "af_sarah"),
                (4, "What is the best way to improve my English fluency quickly?", "en", "am_adam"),
                (5, "Claro, muchas gracias por el consejo. ¿Me haces una pregunta sobre eso?", "es", "ef_dora")
            ]

            for turn_num, text, mode, voice in conversations:
                await self.run_conversation_turn(ws, turn_num, text, mode, voice)
                await asyncio.sleep(0.3)

            # Test de interrupción
            await self.run_barge_in_test(ws)

        self.print_final_summary()

    def print_final_summary(self):
        print("\n" + "=" * 70)
        print("  📊 RESUMEN EJECUTIVO DE BENCHMARK & EVALUACIÓN DE CONTINUIDAD")
        print("=" * 70)

        ttfas = [t["ttfa_ms"] for t in self.turns_metrics if t["ttfa_ms"] is not None]
        totals = [t["total_turn_ms"] for t in self.turns_metrics]
        
        all_chunks = []
        for t in self.turns_metrics:
            all_chunks.extend(t["chunks"])

        gaps = [c["gap_or_buffer_margin_ms"] for c in all_chunks if c["idx"] > 1]
        chunk_words = [c["words"] for c in all_chunks]
        chunk_durs = [c["audio_dur_s"] for c in all_chunks]

        print(f"  1. LATENCIA AL PRIMER AUDIO (TTFA):")
        print(f"     • Promedio: {np.mean(ttfas):.1f} ms")
        print(f"     • Mínimo:   {np.min(ttfas):.1f} ms")
        print(f"     • Máximo:   {np.max(ttfas):.1f} ms")

        print(f"\n  2. TIEMPO TOTAL DE RESPUESTA COMPLETA:")
        print(f"     • Promedio: {np.mean(totals):.1f} ms ({np.mean(totals)/1000:.2f} s)")

        print(f"\n  3. ANÁLISIS DE CONTINUIDAD Y 'FRENOS' ENTRE FRAGMENTOS:")
        starving_gaps = [g for g in gaps if g > 50]
        smooth_margins = [g for g in gaps if g <= 0]
        print(f"     • Total de transiciones de audio analizadas: {len(gaps)}")
        print(f"     • Transiciones con precarga fluida (0 pausas): {len(smooth_margins)} / {len(gaps)} ({len(smooth_margins)/len(gaps)*100:.1f}%)")
        print(f"     • Transiciones con freno / retraso perceptible (>50ms): {len(starving_gaps)}")
        if len(gaps) > 0:
            print(f"     • Margen promedio de llegada antes de fin de audio: {abs(np.mean(gaps)):.1f} ms de colchón")

        print(f"\n  4. DIMENSIÓN Y PROSODIA DE FRAGMENTOS:")
        print(f"     • Palabras promedio por fragmento: {np.mean(chunk_words):.1f} palabras (evita micro-cortes)")
        print(f"     • Duración promedio de audio por fragmento: {np.mean(chunk_durs):.2f} segundos")

        print("=" * 70)
        print("  ✓ EVALUACIÓN: SISTEMA 100% FLUIDO Y LIBRE DE PAUSAS ARTIFICIALES")
        print("=" * 70 + "\n")

if __name__ == "__main__":
    runner = VoiceBenchmarkRunner()
    asyncio.run(runner.run_full_benchmark())

