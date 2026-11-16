"""
core/plugin_loader.py - Dynamic Plugin & Custom Tools Auto-Discovery Engine
Allows developers to drop any .py file into custom_tools/ and have it automatically
callable by the voice assistant with zero boilerplate.
"""
import os
import sys
import importlib.util
from typing import Dict, Any, List, Optional, Tuple

CUSTOM_TOOLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "custom_tools"))

_LOADED_PLUGINS: Dict[str, Any] = {}

def load_custom_tools(tools_dir: str = CUSTOM_TOOLS_DIR) -> Dict[str, Any]:
    """
    Scans custom_tools/ and dynamically imports all modular tool scripts.
    Returns: Dict[tool_name, module]
    """
    global _LOADED_PLUGINS
    _LOADED_PLUGINS.clear()

    if not os.path.isdir(tools_dir):
        return {}

    for fname in os.listdir(tools_dir):
        if fname.endswith(".py") and not fname.startswith("__"):
            mod_name = fname[:-3]
            file_path = os.path.join(tools_dir, fname)
            try:
                spec = importlib.util.spec_from_file_location(f"custom_tools.{mod_name}", file_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "execute") and hasattr(mod, "TRIGGERS"):
                        tool_id = getattr(mod, "TOOL_NAME", mod_name)
                        _LOADED_PLUGINS[tool_id] = mod
                        print(f"[Plugins] Herramienta modular cargada: {tool_id} (triggers: {len(getattr(mod, 'TRIGGERS', []))})")
            except Exception as e:
                print(f"[Plugins Advertencia] Error cargando {fname}: {e}")

    return _LOADED_PLUGINS

def dispatch_custom_tool(user_text: str, lang: str = "es") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Evaluates user input against all loaded custom tool triggers.
    Returns: (is_handled, spoken_response, tool_id)
    """
    if not _LOADED_PLUGINS:
        load_custom_tools()

    clean_text = user_text.lower().strip()

    for tool_id, mod in _LOADED_PLUGINS.items():
        triggers = getattr(mod, "TRIGGERS", [])
        for trigger in triggers:
            if trigger.lower() in clean_text:
                try:
                    res = mod.execute(user_text, lang=lang)
                    return True, str(res), tool_id
                except Exception as e:
                    return True, f"Error ejecutando {tool_id}: {e}", tool_id

    return False, None, None

def get_loaded_tools_metadata() -> List[Dict[str, Any]]:
    """Returns metadata catalog for all active custom tools."""
    if not _LOADED_PLUGINS:
        load_custom_tools()

    meta = []
    for tool_id, mod in _LOADED_PLUGINS.items():
        meta.append({
            "name": tool_id,
            "description": getattr(mod, "DESCRIPTION", "Sin descripción"),
            "triggers": getattr(mod, "TRIGGERS", []),
            "author": getattr(mod, "AUTHOR", "Comunidad"),
            "version": getattr(mod, "VERSION", "1.0.0")
        })
    return meta
