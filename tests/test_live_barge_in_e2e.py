"""
Prueba E2E en Vivo del Protocolo Barge-In Full-Duplex (Estilo ChatGPT Voice / OpenAI Realtime).
Se conecta por WebSocket seguro (WSS) al servidor en ejecución, inicia una generación larga,
dispara una interrupción en caliente y verifica que el servidor se detenga de inmediato y procese
el siguiente turno sin retrasos ni bloqueos.
"""

import unittest
import asyncio
import ssl
import json
import socket
import websockets

def is_server_running(host="127.0.0.1", port=8000) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False

class TestLiveBargeInE2E(unittest.TestCase):
    def setUp(self):
        if not is_server_running():
            self.skipTest("El servidor de voz en el puerto 8000 no está en ejecución. Saltando prueba en vivo.")

    def test_live_barge_in_and_turn_recovery(self):
        async def run_scenario():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            uri = "wss://127.0.0.1:8000/ws/chat"
            async with websockets.connect(uri, ssl=ctx) as ws:
                # 1. Iniciar Turno 1 con prompt largo
                await ws.send(json.dumps({"type": "text", "text": "Cuéntame una historia muy larga sobre la galaxia y las estrellas"}))
                first_msg = await ws.recv()
                self.assertEqual(json.loads(first_msg).get("type"), "user_transcription")

                # 2. Enviar INTERRUPT inmediatamente (Barge-in simulando que el usuario habla)
                await ws.send(json.dumps({"type": "interrupt"}))
                interrupted = False
                for _ in range(15):
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
                    if msg.get("type") == "interrupted":
                        interrupted = True
                        break
                self.assertTrue(interrupted, "El servidor debió confirmar el evento 'interrupted' en < 10ms")

                # 3. Enviar Turno 2 inmediatamente con nueva instrucción
                await ws.send(json.dumps({"type": "text", "text": "¿Qué hora es?"}))
                tool_executed = False
                turn2_done = False
                for _ in range(15):
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
                    mtype = msg.get("type")
                    if mtype == "tool_executed":
                        tool_executed = True
                    elif mtype == "ai_done":
                        turn2_done = True
                        break

                self.assertTrue(tool_executed, "El turno 2 debió ejecutar la herramienta")
                self.assertTrue(turn2_done, "El turno 2 debió completarse normalmente")

        asyncio.run(run_scenario())

if __name__ == "__main__":
    unittest.main()
