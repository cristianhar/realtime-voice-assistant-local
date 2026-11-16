import sqlite3
import os
import re
import json
import time
import urllib.request
import threading
from typing import List, Dict, Optional, Any
import numpy as np

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

        # 7. Tabla de Embeddings Densos para RAG Semántico (Ollama llama3.2:3b 3072D)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings_cache (
                key_text TEXT PRIMARY KEY,
                vector BLOB NOT NULL,
                doc_type TEXT DEFAULT 'general',
                ref_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # Backfill de embeddings para notas existentes
    try:
        backfill_note_embeddings()
    except Exception:
        pass

def backfill_note_embeddings():
    """Calcula embeddings para todas las notas que aún no estén indexadas."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.id, n.title, n.content
                FROM notes n
                LEFT JOIN embeddings_cache e ON n.id = e.ref_id
                WHERE e.ref_id IS NULL
            """)
            unindexed = cursor.fetchall()
            for r in unindexed:
                index_note_embedding(r["id"], r["title"], r["content"])
    except Exception:
        pass

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

def compute_embedding(text: str) -> Optional[np.ndarray]:
    """
    Obtiene o calcula el vector denso (3072D) usando Ollama llama3.2:3b y caché local SQLite.
    Búsqueda en memoria ultrarrápida (<1ms) si ya está en caché.
    """
    clean_t = text.strip()
    if not clean_t:
        return None

    # 1. Búsqueda en caché SQLite
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vector FROM embeddings_cache WHERE key_text = ?", (clean_t,))
            row = cursor.fetchone()
            if row and row["vector"]:
                return np.frombuffer(row["vector"], dtype=np.float32)
    except Exception:
        pass

    # 2. Inferencia en Ollama /api/embeddings
    try:
        data = json.dumps({
            "model": "llama3.2:3b",
            "prompt": clean_t,
            "keep_alive": -1
        }).encode("utf-8")
        ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        req = urllib.request.Request(
            f"{ollama_url}/api/embeddings",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            vec_list = body.get("embedding")
            if vec_list:
                vec = np.array(vec_list, dtype=np.float32)
                try:
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR REPLACE INTO embeddings_cache (key_text, vector)
                            VALUES (?, ?)
                        """, (clean_t, vec.tobytes()))
                        conn.commit()
                except Exception:
                    pass
                return vec
    except Exception:
        # Fallback silencioso si Ollama no responde
        return None
    return None

def index_note_embedding(note_id: int, title: str, content: str):
    """Indexa semánticamente una nota calculando y asociando su vector denso."""
    full_text = f"{title}: {content}".strip()
    vec = compute_embedding(full_text)
    if vec is not None:
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO embeddings_cache (key_text, vector, doc_type, ref_id)
                    VALUES (?, ?, 'note', ?)
                """, (full_text, vec.tobytes(), note_id))
                conn.commit()
        except Exception:
            pass

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

    # Indexar embedding semántico denso en segundo plano para latencia ultrabaja (<2ms)
    def _async_index(nid: int, t: str, c: str):
        try:
            index_note_embedding(nid, t, c)
        except Exception:
            pass

    threading.Thread(target=_async_index, args=(note_id, clean_title, clean_content), daemon=True).start()

    return note_id

def get_recent_notes(limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content, created_at FROM notes ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

def delete_voice_note(note_id: int) -> bool:
    """Elimina una nota por ID de la base de datos, FTS5 y caché de vectores."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        deleted = cursor.rowcount > 0
        try:
            cursor.execute("DELETE FROM notes_fts WHERE note_id = ?", (note_id,))
            cursor.execute("DELETE FROM embeddings_cache WHERE doc_type = 'note' AND ref_id = ?", (note_id,))
        except Exception:
            pass
        conn.commit()
        return deleted

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

def search_dense_memory(query: str, top_k: int = 3, threshold: float = 0.50) -> List[Dict[str, Any]]:
    """
    Búsqueda semántica densa por similitud de coseno en la memoria de notas.
    Encuentra coincidencias por significado conceptual aunque las palabras exactas no coincidan.
    """
    q_vec = compute_embedding(query)
    if q_vec is None:
        return []

    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0:
        return []

    results = []
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.key_text, e.vector, e.ref_id, n.title, n.content
                FROM embeddings_cache e
                LEFT JOIN notes n ON e.ref_id = n.id
                WHERE e.doc_type = 'note'
            """)
            rows = cursor.fetchall()
            for r in rows:
                if not r["vector"]:
                    continue
                doc_vec = np.frombuffer(r["vector"], dtype=np.float32)
                d_norm = np.linalg.norm(doc_vec)
                if d_norm == 0:
                    continue
                score = float(np.dot(q_vec, doc_vec) / (q_norm * d_norm))
                if score >= threshold:
                    title = r["title"] or "Nota"
                    content = r["content"] or r["key_text"]
                    results.append({
                        "id": r["ref_id"],
                        "title": title,
                        "content": content,
                        "score": round(score, 3)
                    })
    except Exception:
        return []

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

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
    RAG Híbrido Contextual Avanzado (Dense Semantic Vector + FTS5 Keyword Match):
    1. Inyecta perfil de usuario (Cristian Arboleda, nivel de inglés, intereses).
    2. Búsqueda Híbrida:
       - Similitud de Coseno en vectores densos (Ollama llama3.2:3b 3072D).
       - Búsqueda léxica indexada en FTS5.
       - Fusión y deduplicación inteligente.
    3. Si es una conversación general sin consulta específica, inyecta notas recientes y vocabulario.
    """
    profile = get_user_profile()
    parts = []

    # 1. Perfil del Usuario
    if profile:
        name = profile.get("name", "Cristian Arboleda")
        level = profile.get("english_level", "B2")
        interests = profile.get("interests", "")
        parts.append(f"PERFIL DEL USUARIO: Hablas con {name}. Nivel inglés: {level}. Intereses: {interests}.")

    # 2. Búsqueda contextual Híbrida (Dense Vector + FTS5)
    has_inquiry = False
    if query:
        inquiry_triggers = [
            "te acuerdas", "recuerdas", "notas", "hablamos", "dije", "dijiste",
            "remember", "notes", "talked", "mentioned", "comprar", "reunión", "clave",
            "qué tenía", "que tenia", "que anote", "qué anoté", "busca", "search"
        ]
        q_lower = query.lower()
        if any(t in q_lower for t in inquiry_triggers):
            has_inquiry = True

            # Vector Dense Search (Cosine similarity)
            dense_notes = search_dense_memory(query, top_k=3, threshold=0.50)
            # FTS5 Keyword Search
            fts_results = search_fts_memory(query, limit=3)

            # Fusión híbrida de notas (Deduplicación por contenido)
            seen_contents = set()
            hybrid_notes = []
            for d in dense_notes:
                key = d["content"].lower().strip()
                seen_contents.add(key)
                hybrid_notes.append(f"'{d['title']}: {d['content']}' (semántica {int(d['score']*100)}%)")

            for n in fts_results.get("notes", []):
                key = n["content"].lower().strip()
                if key not in seen_contents:
                    seen_contents.add(key)
                    hybrid_notes.append(f"'{n['title']}: {n['content']}'")

            if hybrid_notes:
                parts.append(f"NOTAS RELEVANTES ENCONTRADAS (RAG HÍBRIDO): [{'; '.join(hybrid_notes)}]")
            if fts_results.get("messages"):
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
            cursor.execute("DELETE FROM embeddings_cache")
        except Exception:
            pass
        conn.commit()
