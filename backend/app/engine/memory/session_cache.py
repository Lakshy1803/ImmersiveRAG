import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.storage.relations_db import get_connection
from app.core.config import config

def get_query_hash(agent_id: str, query: str) -> str:
    """Creates a deterministic hash for a given query to check for exact semantic matches."""
    payload = f"{agent_id}:{query.strip().lower()}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

class EphemeralSessionCache:
    """Manages the sliding window memory limit for LangGraph agents in SQLite."""

    def __init__(self, session_id: str, agent_id: str):
        self.session_id = session_id
        self.agent_id = agent_id

    def touch_session(self):
        """Creates or updates the last_accessed_at for a session."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agent_sessions (session_id, agent_id) 
                VALUES (?, ?)
                ON CONFLICT(session_id) DO UPDATE SET 
                last_accessed_at = CURRENT_TIMESTAMP,
                interaction_count = interaction_count + 1
            ''', (self.session_id, self.agent_id))
            conn.commit()

    def get_cached_context(self, query: str) -> Optional[Dict[str, Any]]:
        """Checks if this exact query was recently asked in this session."""
        q_hash = get_query_hash(self.agent_id, query)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT context_payload 
                FROM session_context_cache 
                WHERE session_id = ? AND query_hash = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (self.session_id, q_hash))
            row = cursor.fetchone()
            if row:
                return json.loads(row['context_payload'])
        return None

    def save_context(self, query: str, context_payload: Dict[str, Any]):
        """Saves a query's retrieved context into the sliding window. Prunes old entries."""
        self.touch_session()
        q_hash = get_query_hash(self.agent_id, query)
        payload_str = json.dumps(context_payload)

        with get_connection() as conn:
            cursor = conn.cursor()
            # Insert new context
            cursor.execute('''
                INSERT INTO session_context_cache (session_id, query_hash, query_text, context_payload)
                VALUES (?, ?, ?, ?)
            ''', (self.session_id, q_hash, query, payload_str))
            
            # Enforce sliding window (keep only N most recent for this session)
            cursor.execute('''
                DELETE FROM session_context_cache 
                WHERE id NOT IN (
                    SELECT id FROM session_context_cache
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ) AND session_id = ?
            ''', (self.session_id, config.sliding_window_size, self.session_id))
            
            conn.commit()
