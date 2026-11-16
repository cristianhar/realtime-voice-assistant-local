import time
from kokoro_onnx import Kokoro
import sounddevice as sd
import numpy as np

print("Testing Kokoro voice synthesis...")
kokoro = Kokoro('models/kokoro-v0_19.onnx', 'models/voices.bin')
samples, sr = kokoro.create("Hello! Everything is working perfectly.", voice="af_sarah", speed=1.0)
print(f"Generated {len(samples)} samples at {sr} Hz. Playing through speakers...")
sd.play(samples, sr)
sd.wait()
print("Playback complete!")

