import asyncio
import json
import websockets
import time

async def test_spanish_flow():
    uri = "ws://127.0.0.1:8000/ws/chat"
    async with websockets.connect(uri) as ws:
        print("Connected to WebSocket.")
        
        # 1. Set mode to Spanish and voice to ef_dora
        await ws.send(json.dumps({"type": "set_mode", "mode": "es"}))
        await ws.send(json.dumps({"type": "set_voice", "voice": "ef_dora"}))
        
        # 2. Send text message in Spanish
        t0 = time.time()
        turn_id = f"test-{int(t0*1000)}"
        await ws.send(json.dumps({
            "type": "text",
            "turn_id": turn_id,
            "text": "Hola, ¿cómo estás hoy? Cuéntame qué tal va tu día."
        }))
        
        audio_chunks_received = 0
        ai_text = ""
        ttfa = None
        
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(msg)
            m_type = data.get("type")
            
            if m_type == "ai_chunk":
                ai_text += data.get("delta", "")
            elif m_type == "audio_chunk":
                if audio_chunks_received == 0:
                    ttfa = (time.time() - t0) * 1000
                audio_chunks_received += 1
                b64_len = len(data.get("audio", ""))
                chunk_txt = data.get("text", "")
                print(f"  [Audio chunk #{audio_chunks_received}] '{chunk_txt}' (audio bytes b64: {b64_len})")
            elif m_type == "ai_done":
                total_time = (time.time() - t0) * 1000
                print(f"\nAI Done! Full text: '{ai_text.strip()}'")
                print(f"TTFA (Time to First Audio): {ttfa:.1f} ms")
                print(f"Total Turn Time: {total_time:.1f} ms")
                print(f"Total Audio Chunks: {audio_chunks_received}")
                break

asyncio.run(test_spanish_flow())

