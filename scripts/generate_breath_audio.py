"""
generate_breath_audio.py - Generates an organic, subtle human pre-speech micro-inhalation WAV.
"""
import os
import wave
import struct
import math
import random

def generate_subtle_breath(output_path: str, duration_sec: float = 0.09, sample_rate: int = 24000):
    num_samples = int(duration_sec * sample_rate)
    samples = []
    
    # Pink noise filter state
    b0, b1, b2, b3, b4, b5, b6 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    
    # Simple IIR 2-pole bandpass resonant filter for vocal tract inhalation (center ~1800 Hz)
    freq = 1800.0
    q = 1.8
    w0 = 2 * math.pi * freq / sample_rate
    alpha = math.sin(w0) / (2 * q)
    b_bp0 = alpha
    b_bp1 = 0.0
    b_bp2 = -alpha
    a_bp0 = 1.0 + alpha
    a_bp1 = -2.0 * math.cos(w0)
    a_bp2 = 1.0 - alpha
    
    x1, x2, y1, y2 = 0.0, 0.0, 0.0, 0.0
    
    for i in range(num_samples):
        # Progress 0.0 to 1.0
        t = i / float(num_samples)
        
        # Inhalation Envelope: smooth rise, gentle soft decay
        # Starts quietly, peaks around 70% of duration
        if t < 0.70:
            env = math.sin((t / 0.70) * (math.pi / 2.0)) ** 1.8
        else:
            env = math.cos(((t - 0.70) / 0.30) * (math.pi / 2.0)) ** 0.8
            
        # White noise
        white = random.uniform(-1.0, 1.0)
        
        # Pink noise approximation (Paul Kellet's filter)
        b0 = 0.99886 * b0 + white * 0.0555179
        b1 = 0.99332 * b1 + white * 0.0750759
        b2 = 0.96900 * b2 + white * 0.1538520
        b3 = 0.86650 * b3 + white * 0.3104856
        b4 = 0.55000 * b4 + white * 0.5329522
        b5 = -0.7616 * b5 - white * 0.0168980
        pink = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362
        b6 = white * 0.115926
        
        # Apply bandpass resonant filter to simulate throat cavity
        x0 = pink
        y0 = (b_bp0 * x0 + b_bp1 * x1 + b_bp2 * x2 - a_bp1 * y1 - a_bp2 * y2) / a_bp0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
        
        # Mix filtered noise with gentle warmth, scale down to subtle level (~ -18 dB)
        val = (y0 * 0.75 + pink * 0.25) * env * 0.16
        val = max(-1.0, min(1.0, val))
        
        # 16-bit PCM integer
        pcm_val = int(val * 32767.0)
        samples.append(pcm_val)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with wave.open(output_path, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        raw_data = struct.pack(f"<{len(samples)}h", *samples)
        wav_file.writeframes(raw_data)
        
    print(f"[OK] Generated subtle breath audio: {output_path} ({len(samples)} samples, {duration_sec*1000:.0f} ms)")

if __name__ == "__main__":
    generate_subtle_breath("static/audio/breath_subtle.wav")
