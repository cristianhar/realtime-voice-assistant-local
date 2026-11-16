import os
import re
import time
import subprocess
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any
import database

DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def _format_time_es(dt: datetime) -> str:
    hour = dt.hour
    minute = dt.minute
    day_name = DAYS_ES[dt.weekday()]
    day_num = dt.day
    month_name = MONTHS_ES[dt.month - 1]
    
    period = "de la mañana" if hour < 12 else ("de la tarde" if hour < 20 else "de la noche")
    h12 = hour % 12
    if h12 == 0:
        h12 = 12
        
    if minute == 0:
        time_str = f"las {h12} en punto" if h12 != 1 else "la una en punto"
    elif minute == 15:
        time_str = f"las {h12} y cuarto" if h12 != 1 else "la una y cuarto"
    elif minute == 30:
        time_str = f"las {h12} y media" if h12 != 1 else "la una y media"
    else:
        time_str = f"las {h12} y {minute}" if h12 != 1 else f"la una y {minute}"
        
    return f"Son {time_str} {period}, del {day_name} {day_num} de {month_name}."

def _format_time_en(dt: datetime) -> str:
    return dt.strftime("It is %I:%M %p on %A, %B %d.")

def query_gpu_status() -> Dict[str, Any]:
    """Consulta estado térmico y memoria VRAM de la GPU NVIDIA vía nvidia-smi."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0 and res.stdout.strip():
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            if len(parts) >= 4:
                gpu_name = parts[0]
                temp_c = int(parts[1])
                mem_used_mb = float(parts[2])
                mem_total_mb = float(parts[3])
                mem_used_gb = round(mem_used_mb / 1024.0, 1)
                mem_total_gb = round(mem_total_mb / 1024.0, 1)
                mem_free_gb = round(mem_total_gb - mem_used_gb, 1)
                return {
                    "available": True,
                    "name": gpu_name,
                    "temperature_c": temp_c,
                    "memory_used_gb": mem_used_gb,
                    "memory_total_gb": mem_total_gb,
                    "memory_free_gb": mem_free_gb
                }
    except Exception:
        pass
    return {"available": False}

def _launch_target_app(target: str) -> Optional[Dict[str, str]]:
    """Ejecuta de forma segura una aplicación del sistema o abre un servicio."""
    target = target.lower().strip()
    if any(k in target for k in ["calc", "calculadora", "calculator"]):
        subprocess.Popen(["calc.exe"])
        return {"es": "la calculadora", "en": "Calculator"}
    if any(k in target for k in ["notepad", "bloc de notas", "notas"]):
        subprocess.Popen(["notepad.exe"])
        return {"es": "el Bloc de Notas", "en": "Notepad"}
    if any(k in target for k in ["code", "vs code", "visual studio code"]):
        subprocess.Popen(["code"], shell=True)
        return {"es": "Visual Studio Code", "en": "Visual Studio Code"}
    if "spotify" in target:
        subprocess.Popen(["cmd", "/c", "start", "spotify:"], shell=True)
        return {"es": "Spotify", "en": "Spotify"}
    if "youtube" in target:
        webbrowser.open("https://www.youtube.com")
        return {"es": "YouTube", "en": "YouTube"}
    if "github" in target:
        webbrowser.open("https://github.com/cristianhar/realtime-voice-assistant-local")
        return {"es": "tu repositorio de GitHub", "en": "your GitHub repository"}
    if any(k in target for k in ["navegador", "browser", "google"]):
        webbrowser.open("https://www.google.com")
        return {"es": "el navegador web", "en": "the web browser"}
    return None

def detect_and_execute_tool(text: str, lang_mode: str = "es") -> Optional[Dict[str, Any]]:
    """
    Analiza el texto del usuario para detectar intenciones de herramientas directas (Tool Calling local).
    Si coincide, ejecuta la acción inmediatamente en SQLite o sistema y retorna la respuesta hablada.
    Retorna None si debe ser procesado por el LLM conversacional.
    """
    clean = text.lower().strip()
    clean_no_punct = re.sub(r'[^\w\s]', '', clean).strip()

    # 1. TOOL: Consultar Hora / Fecha
    time_patterns_es = [
        r'\b(que|qué)\s+hora\s+(es|tienes|será)\b',
        r'\b(dime|dame)\s+la\s+hora\b',
        r'\bla\s+hora\s+por\s+favor\b',
        r'\b(que|qué)\s+(dia|día|fecha)\s+es\s+hoy\b'
    ]
    time_patterns_en = [
        r'\bwhat\s+time\s+is\s+it\b',
        r'\bwhat(\'s|s)\s+the\s+time\b',
        r'\btell\s+me\s+the\s+time\b',
        r'\bwhat\s+(day|date)\s+is\s+(it|today)\b'
    ]
    
    is_time_es = any(re.search(p, clean_no_punct) for p in time_patterns_es)
    is_time_en = any(re.search(p, clean_no_punct) for p in time_patterns_en)
    
    if is_time_es or is_time_en:
        now = datetime.now()
        is_spanish = is_time_es or (lang_mode == "es")
        spoken = _format_time_es(now) if is_spanish else _format_time_en(now)
        display = f"🕒 {spoken}"
        return {
            "tool": "get_current_time",
            "spoken_response": spoken,
            "display_response": display,
            "lang": "es" if is_spanish else "en",
            "data": {"timestamp": now.isoformat()}
        }

    # 2. TOOL: Guardar Nota de Voz / Recordatorio
    # Ejemplos: "Toma nota de comprar café", "Recuérdame llamar al médico", "Take a note buy coffee"
    note_patterns = [
        r'^(toma\s+nota\s+(?:de|que)?|apunta\s+(?:que)?|recu[eé]rdame\s+(?:que)?|guarda\s+(?:una\s+)?nota\s+(?:de|que)?|anota\s+(?:que)?|nota\s*:?)\s+(.+)$',
        r'^(take\s+a\s+note\s*(?:that|:|to)?|remember\s+(?:that|to)?|save\s+a\s+note\s*(?:that|:)?)\s+(.+)$'
    ]
    
    for pat in note_patterns:
        m = re.match(pat, clean_no_punct)
        if m:
            content = m.group(2).strip()
            if len(content) >= 3:
                # Extraer título y contenido
                is_spanish = "take a note" not in m.group(1) and "remember" not in m.group(1) and "save a note" not in m.group(1)
                title = f"Nota: {content[:25]}..." if len(content) > 25 else f"Nota: {content}"
                note_id = database.save_voice_note(content=content, title=title)
                
                if is_spanish or lang_mode == "es":
                    spoken = f"He guardado tu nota: {content}. ¿Deseas hacer algo más?"
                    display = f"📌 Nota #{note_id} guardada: \"{content}\""
                    lang = "es"
                else:
                    spoken = f"Got it, I saved your note: {content}. Anything else?"
                    display = f"📌 Note #{note_id} saved: \"{content}\""
                    lang = "en"
                    
                return {
                    "tool": "save_voice_note",
                    "spoken_response": spoken,
                    "display_response": display,
                    "lang": lang,
                    "data": {"note_id": note_id, "content": content}
                }

    # 3. TOOL: Listar / Leer Notas de Voz
    list_notes_patterns_es = [
        r'\b(cu[aá]les|qu[eé])\s+son\s+mis\s+notas\b',
        r'\b(qu[eé]\s+notas\s+tengo|l[eé]eme\s+mis\s+notas|mu[eé]strame\s+mis\s+notas|mis\s+notas)\b'
    ]
    list_notes_patterns_en = [
        r'\b(what\s+notes\s+do\s+i\s+have|read\s+my\s+notes|show\s+my\s+notes|list\s+my\s+notes)\b'
    ]
    
    is_list_es = any(re.search(p, clean_no_punct) for p in list_notes_patterns_es)
    is_list_en = any(re.search(p, clean_no_punct) for p in list_notes_patterns_en)
    
    if is_list_es or is_list_en:
        notes = database.get_recent_notes(limit=5)
        is_spanish = is_list_es or (lang_mode == "es")
        
        if not notes:
            spoken = "No tienes ninguna nota guardada todavía. Puedes decir: toma nota de algo para empezar." if is_spanish else "You don't have any notes saved yet. Just say: take a note to save one."
            display = "📌 No hay notas guardadas."
        else:
            if is_spanish:
                items = [n["content"] for n in notes]
                if len(items) == 1:
                    spoken = f"Tienes una nota guardada: {items[0]}."
                else:
                    spoken = f"Tienes {len(items)} notas recientes: " + ", luego: ".join(items) + "."
                display = "📌 Notas recientes:\n" + "\n".join([f"• {n['content']}" for n in notes])
            else:
                items = [n["content"] for n in notes]
                spoken = f"You have {len(items)} recent notes: " + ", and: ".join(items) + "."
                display = "📌 Recent notes:\n" + "\n".join([f"• {n['content']}" for n in notes])
                
        return {
            "tool": "list_voice_notes",
            "spoken_response": spoken,
            "display_response": display,
            "lang": "es" if is_spanish else "en",
            "data": {"notes": notes}
        }

    # 4. TOOL: Listar Vocabulario Guardado
    list_vocab_patterns_es = [
        r'\b(qu[eé]\s+vocabulario\s+tengo|cu[aá]les\s+son\s+mis\s+palabras|qu[eé]\s+palabras\s+aprend[ií]|palabras\s+guardadas)\b'
    ]
    list_vocab_patterns_en = [
        r'\b(what\s+vocabulary\s+did\s+i\s+learn|show\s+my\s+vocabulary|what\s+words\s+did\s+i\s+learn)\b'
    ]
    
    is_v_es = any(re.search(p, clean_no_punct) for p in list_vocab_patterns_es)
    is_v_en = any(re.search(p, clean_no_punct) for p in list_vocab_patterns_en)
    
    if is_v_es or is_v_en:
        vocab = database.get_vocabulary_list(limit=5)
        is_spanish = is_v_es or (lang_mode == "es")
        
        if not vocab:
            spoken = "Aún no tienes vocabulario registrado en tu historial de práctica." if is_spanish else "You have no saved vocabulary yet in your practice history."
            display = "📝 No hay vocabulario registrado todavía."
        else:
            phrases = [v["phrase"] for v in vocab]
            if is_spanish:
                spoken = f"Has practicado {len(phrases)} frases recientemente: " + ", y: ".join(phrases) + "."
                display = "📝 Vocabulario reciente:\n" + "\n".join([f"• {v['phrase']}" for v in vocab])
            else:
                spoken = f"You recently practiced {len(phrases)} phrases: " + ", and: ".join(phrases) + "."
                display = "📝 Recent vocabulary:\n" + "\n".join([f"• {v['phrase']}" for v in vocab])
                
        return {
            "tool": "list_vocabulary",
            "spoken_response": spoken,
            "display_response": display,
            "lang": "es" if is_spanish else "en",
            "data": {"vocabulary": vocab}
        }

    # 5. TOOL: Consultar Estado de Hardware / GPU NVIDIA
    hw_patterns_es = [
        r'\b(estado\s+del\s+(?:hardware|sistema|equipo|computador|pc)|c[oó]mo\s+est[aá]\s+(?:la\s+)?gpu|temperatura\s+(?:de\s+la\s+)?gpu|cu[aá]nta\s+vram|memoria\s+de\s+video|rendimiento\s+del\s+(?:sistema|pc))\b'
    ]
    hw_patterns_en = [
        r'\b(hardware\s+status|system\s+status|how\s+is\s+the\s+gpu|gpu\s+temp|gpu\s+temperature|vram\s+usage|video\s+memory|pc\s+performance)\b'
    ]

    is_hw_es = any(re.search(p, clean_no_punct) for p in hw_patterns_es)
    is_hw_en = any(re.search(p, clean_no_punct) for p in hw_patterns_en)

    if is_hw_es or is_hw_en:
        gpu_info = query_gpu_status()
        is_spanish = is_hw_es or (lang_mode == "es")

        if gpu_info.get("available"):
            name = gpu_info["name"]
            temp = gpu_info["temperature_c"]
            used = gpu_info["memory_used_gb"]
            total = gpu_info["memory_total_gb"]
            free = gpu_info["memory_free_gb"]

            if is_spanish:
                spoken = f"Tu GPU {name} está a {temp} grados, con {used} gigabytes de VRAM ocupados de {total} gigas totales. Tienes {free} gigabytes libres."
                display = f"⚡ GPU: {name} | Temp: {temp}°C | VRAM: {used}/{total} GB ({free} GB libres)"
                lang = "es"
            else:
                spoken = f"Your {name} GPU is at {temp} degrees Celsius, using {used} gigabytes of VRAM out of {total} gigas. You have {free} gigabytes free."
                display = f"⚡ GPU: {name} | Temp: {temp}°C | VRAM: {used}/{total} GB ({free} GB free)"
                lang = "en"
        else:
            if is_spanish:
                spoken = "El sistema está respondiendo con normalidad y los modelos locales están listos en memoria."
                display = "⚡ Sistema activo | Modelos locales cargados en memoria."
                lang = "es"
            else:
                spoken = "System performance is optimal and all local models are loaded and ready in memory."
                display = "⚡ System active | Local models loaded in memory."
                lang = "en"

        return {
            "tool": "get_hardware_status",
            "spoken_response": spoken,
            "display_response": display,
            "lang": lang,
            "data": gpu_info
        }

    # 6. TOOL: Ejecutar o Abrir Aplicaciones Locales / Enlaces
    launch_match = re.search(r'\b(?:abre|abrir|ejecuta|lanzar|lanza|inicia|open|launch|start|run)\s+(?:la\s+|el\s+|the\s+)?([a-z0-9\s]+)\b', clean_no_punct)
    if launch_match:
        target_str = launch_match.group(1).strip()
        launched = _launch_target_app(target_str)
        if launched:
            is_spanish = (lang_mode == "es") or any(k in clean_no_punct for k in ["abre", "abrir", "ejecuta", "lanzar", "lanza", "inicia"])
            user_profile = database.get_user_profile()
            user_name = user_profile.get("name", "Cristian").split()[0]

            if is_spanish:
                app_label = launched["es"]
                spoken = f"Listo {user_name}, he abierto {app_label} para ti."
                display = f"🚀 Aplicación abierta: {app_label}"
                lang = "es"
            else:
                app_label = launched["en"]
                spoken = f"Sure {user_name}, I opened {app_label} for you."
                display = f"🚀 Application opened: {app_label}"
                lang = "en"

            return {
                "tool": "launch_application",
                "spoken_response": spoken,
                "display_response": display,
                "lang": lang,
                "data": {"target": target_str, "app": app_label}
            }

    return None

