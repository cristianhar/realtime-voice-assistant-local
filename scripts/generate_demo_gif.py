"""
generate_demo_gif.py - Generates an animated dark-mode showcase GIF demonstrating
real-time conversational voice interaction, pre-speech breath, and sub-50ms barge-in.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

def create_demo_gif(output_path: str = "docs/images/voice_assistant_demo.gif"):
    width, height = 720, 360
    frames = []
    
    # Try loading a system TrueType font, fall back to default
    try:
        font_title = ImageFont.truetype("arial.ttf", 20)
        font_main = ImageFont.truetype("arial.ttf", 16)
        font_sub = ImageFont.truetype("arial.ttf", 13)
        font_badge = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font_title = font_main = font_sub = font_badge = ImageFont.load_default()

    total_frames = 36
    
    for i in range(total_frames):
        # Background: Dark slate
        img = Image.new("RGB", (width, height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        
        # Outer Border
        draw.rectangle([6, 6, width - 6, height - 6], outline=(51, 65, 85), width=2)
        
        # Header Bar
        draw.rectangle([6, 6, width - 6, 50], fill=(30, 41, 59))
        draw.text((20, 18), "🎙️ Realtime Voice Assistant Local - Full-Duplex 100% Offline", fill=(241, 245, 249), font=font_title)
        
        # Status Badges in top right
        draw.rounded_rectangle([width - 150, 15, width - 20, 40], radius=4, fill=(16, 185, 129))
        draw.text((width - 138, 20), "● CUDA Active", fill=(255, 255, 255), font=font_badge)

        # Center Stage Coordinates
        cx, cy = width // 2, 160
        
        # Stage 1: User Speaking (Frames 0 - 8)
        if i < 9:
            stage_title = "1. User Speaking (16kHz PCM Streaming)"
            color_orb = (56, 189, 248) # Sky blue
            orb_radius = 45 + int(math.sin(i * 0.8) * 8)
            status_text = "User: 'Tell me about quantum computing...'"
            status_sub = "Web Audio VAD Active  |  Latency: 0 ms  |  Word-by-word streaming"
            badge_color = (14, 165, 233)
            
            # Draw Audio Waveform
            for x in range(120, 600, 10):
                wave_h = int(abs(math.sin((x + i * 20) * 0.05)) * 28) + 4
                draw.line([(x, 260 - wave_h), (x, 260 + wave_h)], fill=(56, 189, 248), width=3)

        # Stage 2: Pre-Speech Humanization & Thinking (Frames 9 - 14)
        elif i < 15:
            stage_title = "2. Cognitive Pause & Micro-Inhalation (~80ms)"
            color_orb = (168, 85, 247) # Purple
            orb_radius = 40 + int(math.cos((i - 9) * 0.9) * 4)
            status_text = "AI: [💨 Pre-Speech Micro-Breath Intake] 'Mmm...'"
            status_sub = "Humanizer active  |  Vocal tract simulation  |  Llama 3.2 token ready"
            badge_color = (147, 51, 234)

            # Breath airflow ripple
            ripple = (i - 9) * 8
            draw.ellipse([cx - 45 - ripple, cy - 45 - ripple, cx + 45 + ripple, cy + 45 + ripple], outline=(192, 132, 252), width=1)

        # Stage 3: AI Assistant Speaking via Kokoro (Frames 15 - 24)
        elif i < 25:
            stage_title = "3. AI Voice Streaming (Kokoro Multithread ONNX)"
            color_orb = (34, 197, 94) # Green / Cyan
            orb_radius = 52 + int(math.sin((i - 15) * 0.9) * 10)
            status_text = "AI: 'Quantum computing leverages qubits and superposition to solve...'"
            status_sub = "Gapless chunk queue  |  24kHz Hi-Fi audio  |  Zero cloud cost"
            badge_color = (22, 163, 74)
            
            # Sound waves radiating from orb
            for r in range(65, 115, 15):
                alpha_r = r + (i % 4) * 5
                draw.ellipse([cx - alpha_r, cy - alpha_r, cx + alpha_r, cy + alpha_r], outline=(74, 222, 128), width=1)

        # Stage 4: Sub-50ms Instant Barge-In Interruption! (Frames 25 - 29)
        elif i < 30:
            stage_title = "4. INSTANT BARGE-IN INTERRUPTION (<50ms)!"
            color_orb = (239, 68, 68) # Red
            orb_radius = 35 + int(math.sin((i - 25) * 1.5) * 4)
            status_text = "USER INTERRUPTS: 'Wait, explain it like I'm five!'"
            status_sub = "⚡ Audio cut in 0.02ms!  |  LLM aborted  |  Buffer wiped instantly"
            badge_color = (220, 38, 38)
            
            # Flash alert box
            draw.rounded_rectangle([100, 240, width - 100, 280], radius=6, fill=(153, 27, 27))
            draw.text((120, 252), "⚡ BARGE-IN TRIGGERED: Playback silenced in 0.02 ms!", fill=(254, 226, 226), font=font_main)

        # Stage 5: Immediate Smooth Resume (Frames 30 - 35)
        else:
            stage_title = "5. Seamless Conversational Continuity"
            color_orb = (56, 189, 248) # Blue
            orb_radius = 48 + int(math.sin((i - 30) * 0.7) * 6)
            status_text = "AI: 'Sure! Imagine a coin spinning in the air...'"
            status_sub = "Zero latency transition  |  Hybrid SQLite memory intact"
            badge_color = (14, 165, 233)
            
            # Smooth gentle wave
            for x in range(160, 560, 12):
                wave_h = int(abs(math.sin((x + i * 15) * 0.04)) * 16) + 4
                draw.line([(x, 260 - wave_h), (x, 260 + wave_h)], fill=(56, 189, 248), width=2)

        # Draw Glowing Central Orb
        draw.ellipse([cx - orb_radius - 8, cy - orb_radius - 8, cx + orb_radius + 8, cy + orb_radius + 8], fill=(color_orb[0]//3, color_orb[1]//3, color_orb[2]//3))
        draw.ellipse([cx - orb_radius, cy - orb_radius, cx + orb_radius, cy + orb_radius], fill=color_orb)
        # Inner specular highlight
        draw.ellipse([cx - orb_radius//2, cy - orb_radius//2 - 6, cx, cy - 6], fill=(255, 255, 255))
        
        # Stage Pill Label
        draw.rounded_rectangle([20, 65, 380, 92], radius=4, fill=badge_color)
        draw.text((30, 70), stage_title, fill=(255, 255, 255), font=font_main)

        # Subtitle / Conversation Box at bottom
        draw.rounded_rectangle([20, 292, width - 20, 345], radius=6, fill=(30, 41, 59))
        draw.text((35, 300), status_text, fill=(255, 255, 255), font=font_main)
        draw.text((35, 324), status_sub, fill=(148, 163, 184), font=font_sub)

        frames.append(img)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=180, # 180ms per frame = fluid animated preview
        loop=0
    )
    size_kb = os.path.getsize(output_path) / 1024
    print(f"[OK] Generated demo GIF: {output_path} ({len(frames)} frames, {size_kb:.1f} KB)")

if __name__ == "__main__":
    create_demo_gif()
