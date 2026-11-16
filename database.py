import sqlite3
import os
import re
import json
import time
from typing import List, Dict, Optional, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "voice_assistant.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa el esquema de SQLite si no existe."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Tabla de sesiones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                language_mode TEXT DEFAULT 'en',
                voice_name TEXT DEFAULT 'af_sarah',
                total_turns INTEGER DEFAULT 0
            )
        """)
        
        # 2. Tabla de mensajes conversacionales
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                translation TEXT,
                stt_ms INTEGER,
                ttfa_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        
        # 3. Tabla de vocabulario aprendido y correcciones pedagógicas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase TEXT NOT NULL UNIQUE,
                correction TEXT,
                tip TEXT,
                language TEXT DEFAULT 'en',
                times_seen INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Tabla de notas y recordatorios creados por voz (Tool Calling)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Tabla de perfil y preferencias del usuario (Memoria de Usuario)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. Tablas virtuales FTS5 para búsqueda semántica / texto completo
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                note_id UNINDEXED,
                title,
                content
            )
        """)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                msg_id UNINDEXED,
                role UNINDEXED,
                content
            )
        """)

        # Inicializar perfil por defecto de Cristian Arboleda si no existe
        default_profile = {
            "name": "Cristian Arboleda",
            "preferred_language": "es",
            "english_level": "Intermedio (B2)",
            "interests": "Programación, Inteligencia Artificial, GPUs NVIDIA, Robótica"
        }
        for k, v in default_profile.items():
            cursor.execute("""
                INSERT OR IGNORE INTO user_profile (key, value) VALUES (?, ?)
            """, (k, v))

        conn.commit()

def create_or_get_session(session_id: str, mode: str = "en", voice: str = "af_sarah") -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "INSERT INTO sessions (id, language_mode, voice_name) VALUES (?, ?, ?)",
                (session_id, mode, voice)
            )
            conn.commit()
        return session_id

def save_message(session_id: str, role: str, content: str, turn_id: Optional[str] = None,
                 translation: Optional[str] = None, stt_ms: Optional[int] = None,
                 ttfa_ms: Optional[int] = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (session_id, turn_id, role, content, translation, stt_ms, ttfa_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, turn_id, role, content, translation, stt_ms, ttfa_ms))
        msg_id = cursor.lastrowid
        cursor.execute("""
            UPDATE sessions SET total_turns = total_turns + 1 WHERE id = ?
        """, (session_id,))
        # Indexar en FTS5 para búsqueda semántica/texto
        try:
            cursor.execute("""
                INSERT INTO messages_fts (msg_id, role, content) VALUES (?, ?, ?)
            """, (msg_id, role, content))
        except Exception:
            pass
        conn.commit()

def update_message_translation(turn_id: str, role: str, translation: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages SET translation = ? WHERE turn_id = ? AND role = ?
        """, (translation, turn_id, role))
        conn.commit()

def save_vocabulary_or_correction(phrase: str, correction: Optional[str] = None, tip: Optional[str] = None, language: str = "en"):
    clean_phrase = phrase.strip()
    if not clean_phrase:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vocabulary (phrase, correction, tip, language, times_seen, last_seen)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(phrase) DO UPDATE SET
                times_seen = times_seen + 1,
                last_seen = CURRENT_TIMESTAMP,
                correction = coalesce(excluded.correction, vocabulary.correction),
                tip = coalesce(excluded.tip, vocabulary.tip)
        """, (clean_phrase, correction, tip, language))
        conn.commit()

def get_recent_messages(limit: int = 15) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, translation, turn_id, stt_ms, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in reversed(rows)]

def get_vocabulary_list(limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT phrase, correction, tip, language, times_seen, last_seen
            FROM vocabulary
            ORDER BY last_seen DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def save_voice_note(content: str, title: Optional[str] = None) -> int:
    clean_title = title or f"Nota de voz ({time.strftime('%d/%m %H:%M')})"
    clean_content = content.strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (title, content) VALUES (?, ?)
        """, (clean_title, clean_content))
        note_id = cursor.lastrowid
        # Indexar en FTS5
        try:
            cursor.execute("""
                INSERT INTO notes_fts (note_id, title, content) VALUES (?, ?, ?)
            """, (note_id, clean_title, clean_content))
        except Exception:
            pass
        conn.commit()
        return note_id

def get_recent_notes(limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content, created_at FROM notes ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

def get_user_profile() -> Dict[str, str]:
    """Retorna las propiedades y preferencias del usuario."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM user_profile")
        return {r["key"]: r["value"] for r in cursor.fetchall()}

def set_user_profile_value(key: str, value: str):
    """Actualiza o crea una propiedad en el perfil del usuario."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_profile (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """, (key, value.strip()))
        conn.commit()

def search_fts_memory(query: str, limit: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """Busca en tablas virtuales FTS5 notas y mensajes coincidentes por palabras clave."""
    clean_q = re.sub(r'[^\w\s]', '', query).strip()
    words = [
        w for w in clean_q.split()
        if len(w) >= 3 and w.lower() not in {
            "como", "donde", "cuando", "pero", "para", "sobre", "with", "this",
            "that", "what", "where", "have", "been", "from", "cual", "cuales", "hola"
        }
    ]
    if not words:
        return {"notes": [], "messages": []}

    match_query = " OR ".join([f'"{w}"*' for w in words])
    with get_connection() as conn:
        cursor = conn.cursor()
        notes = []
        messages = []
        try:
            cursor.execute("""
                SELECT title, content FROM notes_fts WHERE notes_fts MATCH ? LIMIT ?
            """, (match_query, limit))
            notes = [dict(r) for r in cursor.fetchall()]
        except Exception:
            pass

        try:
            cursor.execute("""
                SELECT role, content FROM messages_fts WHERE messages_fts MATCH ? LIMIT ?
            """, (match_query, limit))
            messages = [dict(r) for r in cursor.fetchall()]
        except Exception:
            pass

        return {"notes": notes, "messages": messages}

def get_smart_memory_context(query: Optional[str] = None) -> str:
    """
    RAG Híbrido Contextual Avanzado:
    1. Inyecta perfil de usuario (Cristian Arboleda, nivel de inglés, intereses).
    2. Si el query consulta sobre temas pasados, realiza búsqueda indexada en FTS5.
    3. Si es una conversación general, añade las notas más recientes y vocabulario.
    """
    profile = get_user_profile()
    parts = []

    # 1. Perfil del Usuario
    if profile:
        name = profile.get("name", "Cristian Arboleda")
        level = profile.get("english_level", "B2")
        interests = profile.get("interests", "")
        parts.append(f"PERFIL DEL USUARIO: Hablas con {name}. Nivel inglés: {level}. Intereses: {interests}.")

    # 2. Búsqueda contextual FTS5 si hay query orientada a recuerdos/notas
    has_inquiry = False
    if query:
        inquiry_triggers = [
            "te acuerdas", "recuerdas", "notas", "hablamos", "dije", "dijiste",
            "remember", "notes", "talked", "mentioned", "comprar", "reunión", "clave"
        ]
        q_lower = query.lower()
        if any(t in q_lower for t in inquiry_triggers):
            has_inquiry = True
            fts_results = search_fts_memory(query, limit=3)
            if fts_results["notes"]:
                notes_text = "; ".join([f"'{n['title']}: {n['content']}'" for n in fts_results["notes"]])
                parts.append(f"NOTAS RELEVANTES ENCONTRADAS POR BÚSQUEDA: [{notes_text}]")
            if fts_results["messages"]:
                msgs_text = "; ".join([f"{m['role']}: '{m['content']}'" for m in fts_results["messages"]])
                parts.append(f"CONVERSACIONES PREVIAS RELEVANTES: [{msgs_text}]")

    # 3. Fallback a últimas notas si no hubo consulta específica
    if not has_inquiry:
        recent_notes = get_recent_notes(limit=3)
        if recent_notes:
            notes_str = "; ".join([f"{n['title']}: {n['content']}" for n in recent_notes])
            parts.append(f"NOTAS RECIENTES GUARDADAS: [{notes_str}]")

    vocab = get_vocabulary_list(limit=3)
    if vocab:
        v_str = "; ".join([f"\"{v['phrase']}\"" for v in vocab])
        parts.append(f"VOCABULARIO CLAVE PRACTICADO: [{v_str}]")

    if not parts:
        return ""
    return "\n\n[MEMORIA PERSISTENTE Y CONTEXTO RAG]\n" + "\n".join(parts)

def get_memory_context_string(limit_notes: int = 5, limit_vocab: int = 5) -> str:
    """Compatibilidad con versiones previas."""
    return get_smart_memory_context()

def clear_all_history():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM sessions")
        cursor.execute("DELETE FROM vocabulary")
        cursor.execute("DELETE FROM notes")
        try:
            cursor.execute("DELETE FROM notes_fts")
            cursor.execute("DELETE FROM messages_fts")
        except Exception:
            pass
        conn.commit()
