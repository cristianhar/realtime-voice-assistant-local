# SQLite Memory Architecture for Voice AI

## Schema Design

### 1. `conversation_turns` (Episodic Memory)
Maintains conversational history for immediate sliding-window context injection:
```sql
CREATE TABLE IF NOT EXISTS conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,          -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_turns_time ON conversation_turns(timestamp);
```

### 2. `notes_fts` (Semantic Full-Text Search via FTS5)
Enables BM25 ranked queries across voice notes, meeting transcripts, and user facts without external vector database servers:
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    title,
    content,
    tokenize='porter unicode61'
);
```

### 3. `user_profile` (Long-Term Semantic Preferences)
Key-value store holding the user's permanent preferences (name, language, preferred voice rate, system paths):
```sql
CREATE TABLE IF NOT EXISTS user_profile (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```
