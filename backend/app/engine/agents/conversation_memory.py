"""
3-tier conversation memory for LangGraph agents.

Tier 1: Turn-level context cache (existing session_context_cache) — dedup identical queries
Tier 2: Conversation message log (conversation_messages) — full audit trail
Tier 3: Rolling summary digest (agent_sessions.summary_digest) — cheap LLM context
"""
import json
import logging
from typing import List, Dict, Any, Optional

from app.storage.relations_db import get_connection
from app.core.config import config

logger = logging.getLogger(__name__)

# Simple token estimator (avoids tiktoken dependency for speed)
def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class ConversationMemory:
    """Manages the conversation history and rolling summary for a session + agent pair."""

    def __init__(self, session_id: str, agent_id: str):
        self.session_id = session_id
        self.agent_id = agent_id

    def touch_session(self):
        """Creates or updates the session record."""
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

    def append_turn(self, role: str, content: str):
        """Saves a single message to the conversation log."""
        self.touch_session()
        token_count = _estimate_tokens(content)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_messages (session_id, agent_id, role, content, token_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.session_id, self.agent_id, role, content, token_count))
            conn.commit()

    def get_recent_turns(self, n: int = 4) -> List[Dict[str, str]]:
        """Returns the last N messages for building the LLM prompt."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT role, content FROM conversation_messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (self.session_id, n))
            rows = cursor.fetchall()
        # Reverse to chronological order
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def get_turn_count(self) -> int:
        """Returns total number of messages in this session."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM conversation_messages WHERE session_id = ?",
                (self.session_id,)
            )
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    def get_summary_digest(self) -> str:
        """Returns the rolling summary digest for this session."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT summary_digest FROM agent_sessions WHERE session_id = ?",
                (self.session_id,)
            )
            row = cursor.fetchone()
            return row["summary_digest"] if row and row["summary_digest"] else ""

    def save_summary_digest(self, summary: str):
        """Persists the rolling summary digest."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agent_sessions SET summary_digest = ? WHERE session_id = ?",
                (summary, self.session_id)
            )
            conn.commit()

    def maybe_refresh_summary(self):
        """
        Every 4th turn, generate a new rolling summary from older messages.
        Uses the LLM to compress older history into ≤256 tokens.
        """
        turn_count = self.get_turn_count()
        if turn_count < 8 or turn_count % 4 != 0:
            return  # Only refresh every 4th turn, starting after 8 messages

        try:
            from app.engine.agents.llm_client import get_sync_llm_client

            # Get older messages (skip the last 4 which are "recent")
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT role, content FROM conversation_messages
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                ''', (self.session_id,))
                all_rows = cursor.fetchall()

            # Older messages = everything except the last 4
            older = all_rows[:-4] if len(all_rows) > 4 else []
            if not older:
                return

            # Build a condensed transcript
            transcript = "\n".join(
                f"{r['role'].upper()}: {r['content'][:200]}" for r in older
            )

            client = get_sync_llm_client()
            response = client.chat.completions.create(
                model=config.llm_model,
                messages=[
                    {"role": "system", "content": "Summarize this conversation in 3 sentences or fewer. Be extremely concise."},
                    {"role": "user", "content": transcript[:2000]}
                ],
                max_tokens=config.history_summary_max_tokens,
                temperature=0.3
            )
            summary = response.choices[0].message.content.strip()[:1024]
            self.save_summary_digest(summary)
            logger.info(f"Refreshed summary digest for session {self.session_id}")

        except Exception as e:
            logger.warning(f"Failed to refresh summary digest: {e}")

    def build_history_context(self) -> str:
        """
        Builds the history context string for the LLM prompt.
        Combines: rolling summary (older history) + last 4 verbatim turns.
        """
        parts = []

        # Tier 3: Rolling summary of older conversation
        digest = self.get_summary_digest()
        if digest:
            parts.append(f"[Previous conversation summary]\n{digest}")

        # Tier 2: Recent turns verbatim
        recent = self.get_recent_turns(n=4)
        if recent:
            recent_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in recent)
            parts.append(f"[Recent conversation]\n{recent_text}")

        return "\n\n".join(parts)
