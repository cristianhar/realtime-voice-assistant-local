"""
hybrid_sqlite_memory.py - Persistent SQLite Memory with FTS5 Full-Text Search
"""
import sqlite3
import re
from typing import List, Dict, Any

class SQLiteMemoryManager:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._shared_conn = sqlite3.connect(self.db_path) if self.db_path == ":memory:" else None
        self.init_db()

    def get_conn(self):
        if self._shared_conn is not None:
            return self._shared_conn
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                    title, content, tokenize='porter unicode61'
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            conn.commit()

    def save_note(self, title: str, content: str):
        with self.get_conn() as conn:
            conn.cursor().execute("INSERT INTO notes_fts (title, content) VALUES (?, ?);", (title, content))
            conn.commit()

    def search_notes(self, query: str, limit: int = 3) -> List[Dict[str, str]]:
        clean_q = re.sub(r'[^\w\s]', '', query).strip()
        words = [
            w for w in clean_q.split()
            if len(w) >= 3 and w.lower() not in {
                "como", "donde", "cuando", "pero", "para", "sobre", "with", "this",
                "that", "what", "where", "have", "been", "from", "cual", "cuales", "hola"
            }
        ]
        if not words:
            return []

        match_query = " OR ".join([f'"{w}"*' for w in words])
        with self.get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT title, content, rank FROM notes_fts
                    WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?;
                """, (match_query, limit))
                return [{"title": r[0], "content": r[1]} for r in cursor.fetchall()]
            except Exception:
                return []

    def get_context_for_prompt(self, user_text: str) -> str:
        matches = self.search_notes(user_text)
        if not matches:
            return ""
        notes_str = "\n".join([f"- {m['title']}: {m['content']}" for m in matches])
        return f"\nRelevant Memory Notes:\n{notes_str}\n"

if __name__ == "__main__":
    mem = SQLiteMemoryManager()
    mem.save_note("Flight Info", "Flight AA123 departs at 10 AM on Sunday")
    results = mem.search_notes("flight")
    print("FTS5 Match:", results)
    print("Injected Prompt Context:\n", mem.get_context_for_prompt("tell me about my flight"))
