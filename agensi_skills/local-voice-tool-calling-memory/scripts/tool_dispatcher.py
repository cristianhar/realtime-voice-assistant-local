"""
tool_dispatcher.py - Zero-latency (<5ms) deterministic tool dispatcher for voice agents.
Zero external dependencies (uses Python standard library only).
"""
import datetime
import os
import sys
import platform
import subprocess
from typing import Tuple, Optional

def get_system_hardware_summary() -> str:
    """Returns a quick hardware overview using standard library tools."""
    os_name = platform.system()
    gpu_info = "N/A"
    
    # Try nvidia-smi if available
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1.0
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 3:
                gpu_info = f"{parts[0]} ({parts[1]}MB / {parts[2]}MB VRAM)"
    except Exception:
        pass

    return f"OS: {os_name} {platform.release()}, GPU: {gpu_info}"

def dispatch_local_tool(user_text: str, lang: str = "en") -> Tuple[bool, Optional[str]]:
    """
    Evaluates user input against fast heuristic patterns.
    Returns: (is_handled, response_text)
    """
    text_clean = user_text.lower().strip()

    # 1. System Hardware Status
    if any(k in text_clean for k in ["hardware status", "system status", "gpu status", "estado del sistema", "rendimiento"]):
        summary = get_system_hardware_summary()
        if lang == "es" or any(w in text_clean for w in ["sistema", "rendimiento"]):
            return True, f"Estado del sistema: {summary}."
        return True, f"System hardware summary: {summary}."

    # 2. Real-time Clock
    if any(k in text_clean for k in ["what time is it", "current time", "what's the time", "qué hora es", "la hora"]):
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        if lang == "es" or "hora" in text_clean:
            return True, f"Son las {time_str}."
        return True, f"It is currently {time_str}."

    # 3. Application Launcher (Demo safe set)
    app_map = {
        "calculator": "calc", "calculadora": "calc",
        "notepad": "notepad", "bloc de notas": "notepad"
    }
    for trigger, exe in app_map.items():
        if f"open {trigger}" in text_clean or f"abre {trigger}" in text_clean or f"abrir {trigger}" in text_clean:
            try:
                subprocess.Popen(exe)
                return True, f"Opening {trigger}." if lang == "en" else f"Abriendo {trigger}."
            except Exception as e:
                return True, f"Could not launch {trigger}: {e}"

    return False, None

if __name__ == "__main__":
    handled, res = dispatch_local_tool("what time is it?")
    print(f"Handled: {handled} -> Result: {res}")
