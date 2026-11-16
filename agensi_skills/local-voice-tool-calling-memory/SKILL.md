---
name: local-voice-tool-calling-memory
description: Zero-latency local tool calling dispatcher and hybrid SQLite FTS5 persistent memory for voice AI agents. Runs 100% offline without external API costs.
---

# Local Voice Tool Calling & Hybrid SQLite Memory

## Overview
This skill provides AI coding agents with an ultra-fast, zero-cost architecture for **instant local tool execution (<5 ms)** and **persistent hybrid memory (SQLite FTS5 + Semantic RAG)** designed specifically for real-time conversational voice agents.

In conversational voice applications, delegating trivial queries (e.g., system hardware stats, current time, opening local apps, saving quick voice notes) to an external cloud LLM wastes 500-1500 ms and incurs API token costs. This skill enables immediate heuristic tool dispatching with automatic fallback to local or cloud LLMs.

---

## When to Use This Skill
Activate this skill when:
- Building voice agents that need to inspect local hardware (battery, CPU, RAM, GPU VRAM) instantly.
- Creating persistent user memory (facts, preferences, profile) that survives restarts without heavy vector DBs (e.g. Pinecone/Milvus).
- Needing full-text semantic search (FTS5 BM25) for voice notes and conversational transcripts.
- Reducing LLM latency and token costs by intercepting deterministic commands locally.

---

## Core Capabilities

### 1. Zero-Latency Tool Dispatching
Matches user voice intents through optimized heuristic patterns with bilingual support (English/Spanish):
- **Hardware Status**: Battery percentage, CPU load, RAM usage, GPU VRAM.
- **Time & Date**: Natural language local time queries.
- **Voice Notes**: Instant note saving and BM25 search.
- **Application Launcher**: Native OS process launch (Calc, Notepad, Terminal, Spotify).
- **Speech Rate Control**: Live speed adjustment (`faster`, `slower`, `normal`).

### 2. Hybrid SQLite Memory Pipeline
```
[User Turn] ---> [Fast Heuristic Matcher] ---> Match? ---> YES ---> [Execute Tool (<5ms)]
                        |                                                   |
                        NO                                           [Return Voice Result]
                        v
          [Hybrid SQLite Context (FTS5 + Profile)]
                        |
            [Local LLM Ingestion (Llama 3.2)]
```

---

## Bundled Tools & Assets
- `scripts/tool_dispatcher.py`: Production Python tool router with 8 built-in local system tools.
- `scripts/hybrid_sqlite_memory.py`: Self-contained SQLite memory manager with FTS5 virtual tables and dynamic context builder.
- `references/memory_schema.md`: Complete database schema and indexing strategies.
- `templates/init_memory_db.sql`: Ready-to-execute SQLite migration script.

---

## Usage Example for Agents
```python
from scripts.tool_dispatcher import dispatch_local_tool
from scripts.hybrid_sqlite_memory import SQLiteMemoryManager

memory = SQLiteMemoryManager("agent_memory.db")
user_input = "Save a note that the meeting is at 4 PM"

# 1. Check local tools first (<5ms execution)
handled, tool_result, is_done = dispatch_local_tool(user_input, memory_mgr=memory)
if handled:
    print(f"Tool executed immediately: {tool_result}")
else:
    # 2. Inject relevant memories into LLM prompt
    context = memory.get_context_for_prompt(user_input)
    # Stream to LLM with injected context...
```
