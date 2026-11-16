-- init_memory_db.sql: Quick setup for Voice Agent Hybrid Memory
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title,
    content,
    tokenize='porter unicode61'
);

CREATE TABLE IF NOT EXISTS user_profile (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Seed default configuration
INSERT OR IGNORE INTO user_profile (key, value) VALUES ('preferred_lang', 'en');
INSERT OR IGNORE INTO user_profile (key, value) VALUES ('speech_rate', '1.0');
