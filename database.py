import sqlite3
import os
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
        cursor.execute("""
            UPDATE sessions SET total_turns = total_turns + 1 WHERE id = ?
        """, (session_id,))
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (title, content) VALUES (?, ?)
        """, (clean_title, content.strip()))
        conn.commit()
        return cursor.lastrowid

def get_recent_notes(limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content, created_at FROM notes ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

def get_memory_context_string(limit_notes: int = 5, limit_vocab: int = 5) -> str:
    """Genera un bloque de memoria persistente para inyectar en el contexto del LLM."""
    notes = get_recent_notes(limit=limit_notes)
    vocab = get_vocabulary_list(limit=limit_vocab)
    
    parts = []
    if notes:
        notes_items = [f"- {n['title']}: {n['content']}" for n in reversed(notes)]
        parts.append("NOTAS Y RECORDATORIOS GUARDADOS DEL USUARIO:\n" + "\n".join(notes_items))
    if vocab:
        vocab_items = [f"- \"{v['phrase']}\" (Tip: {v['tip'] or 'correct phrasing'})" for v in vocab]
        parts.append("VOCABULARIO Y PUNTOS DE MEJORA DEL USUARIO:\n" + "\n".join(vocab_items))
        
    if not parts:
        return ""
    return "\n\n[MEMORIA PERSISTENTE - CONTEXTO DISPONIBLE]\n" + "\n\n".join(parts)

def clear_all_history():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM sessions")
        cursor.execute("DELETE FROM vocabulary")
        cursor.execute("DELETE FROM notes")
        conn.commit()
