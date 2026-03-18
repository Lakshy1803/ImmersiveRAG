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
    return conn

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
                interaction_count INTEGER DEFAULT 0
            )
        ''')
        
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
