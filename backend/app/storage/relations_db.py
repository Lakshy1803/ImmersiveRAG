import sqlite3
import json
from contextlib import contextmanager
from app.core.config import config
import os

DB_PATH = config.sqlite_db_path.replace('sqlite:///', '')

def get_connection():
    # Ensure data dir exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ── Base Agent Definitions ──────────────────────────────────────────────
_BASE_AGENTS = [
    {
        "agent_id": "doc_analyzer",
        "name": "Document Analyzer",
        "description": "Precise document analyst that answers strictly from provided context.",
        "system_prompt": (
            "You are a precise document analyst for a corporate knowledge base. "
            "Answer the user's question using ONLY the provided context chunks. "
            "If the context does not contain the answer, say so clearly. "
            "Be concise, professional, and cite which chunk informed your answer when possible."
        ),
        "icon": "description",
        "is_system": 1,
        "enabled_tools": '["export_pdf", "export_csv", "generate_template"]'
    },
    {
        "agent_id": "general_assistant",
        "name": "General Assistant",
        "description": "Helpful corporate assistant that uses context when relevant.",
        "system_prompt": (
            "You are a helpful corporate assistant. "
            "Use the provided context chunks if they are relevant to the user's question. "
            "If no relevant context is available, answer from your general knowledge. "
            "Be concise and professional."
        ),
        "icon": "smart_toy",
        "is_system": 1,
        "enabled_tools": '["export_pdf"]'
    },
]

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Ingestion Jobs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                request_data TEXT NOT NULL,
                document_id TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Agent Sessions (for Memory Management)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                interaction_count INTEGER DEFAULT 0,
                summary_digest TEXT DEFAULT ''
            )
        ''')

        # Migration: add summary_digest to existing agent_sessions tables (backwards compat)
        try:
            cursor.execute("ALTER TABLE agent_sessions ADD COLUMN summary_digest TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            pass  # Column already exists — expected for new DBs
        
        # Session Context Cache (The sliding window memory)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_context_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                query_hash TEXT NOT NULL,
                query_text TEXT NOT NULL,
                context_payload TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES agent_sessions (session_id) ON DELETE CASCADE
            )
        ''')

        # Agent Definitions — base (immutable) + user-configured (clones)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_definitions (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                system_prompt TEXT NOT NULL,
                base_agent_id TEXT,
                icon TEXT DEFAULT 'smart_toy',
                config_json TEXT DEFAULT '{}',
                enabled_tools TEXT DEFAULT '[]',
                is_system BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migration: add enabled_tools to existing tables
        try:
            cursor.execute("ALTER TABLE agent_definitions ADD COLUMN enabled_tools TEXT DEFAULT '[]'")
            conn.commit()
        except:
            pass


        # Conversation Message Log — for history + summary generation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES agent_sessions (session_id) ON DELETE CASCADE
            )
        ''')

        # Seed base agents (upsert — doesn't overwrite user edits if they exist)
        for agent in _BASE_AGENTS:
            cursor.execute('''
                INSERT INTO agent_definitions (agent_id, name, description, system_prompt, icon, is_system, enabled_tools)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO NOTHING
            ''', (
                agent["agent_id"], agent["name"], agent["description"],
                agent["system_prompt"], agent["icon"], agent["is_system"], agent.get("enabled_tools", '[]')
            ))
        
        conn.commit()

@contextmanager
def get_db_session():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

# Initialize DB on module load
init_db()

