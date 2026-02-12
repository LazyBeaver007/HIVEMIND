from google import genai
import os
from pathlib import Path
import sqlite3


class HiveMind:
    def __init__(self, api_key=None, model_name="gemini-3-flash-preview"):
        self.api_key = api_key
        self.model = model_name

        
        resolved = api_key or os.getenv("GENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not resolved:
            env_path = Path(__file__).resolve().parent / ".env.local"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k in ("GENAI_API_KEY", "GEMINI_API_KEY") and v:
                            resolved = v
                            break

        if resolved:
            resolved = resolved.strip()
            self.client = genai.Client(api_key=resolved)
            self.api_key = resolved
        else:
            self.client = None
            self.api_key = None

    def extract_entities_and_relations(self, text_chunk):
        prompt = f"""
You are a knowledge graph builder. Extract core scientific entities and their
relationships from this research text.

Output ONLY in this format:
(Entity1, relationship, Entity2)
(Entity2, relationship, Entity3)

Example: (Backpropagation, used_in, Neural Networks)

Text: {text_chunk}
"""
        if self.client:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            return response.text
        
        return "Paper, mentions, Concept" #fallback

    def generate_content(self, prompt):
        if self.client:
            return self.client.models.generate_content(model=self.model, contents=prompt)

        class _Resp:
            def __init__(self, text):
                self.text = text

        return _Resp("[no-api-key]")


class ChatMemory:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add_message(self, session_id, role, content, context=None):
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO messages (session_id, role, content, context) VALUES (?, ?, ?, ?)",
                (session_id, role, content, context),
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_context(self, session_id, limit=6):
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT role, content
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = list(reversed(cur.fetchall()))
        finally:
            conn.close()

        if not rows:
            return ""

        lines = []
        for role, content in rows:
            lines.append(f"{role.capitalize()}: {content}")
        return "\n".join(lines)

    def list_sessions(self, limit=None):
        conn = self._connect()
        try:
            cur = conn.cursor()
            query = (
                "SELECT session_id, MIN(created_at), MAX(created_at), COUNT(*) "
                "FROM messages GROUP BY session_id ORDER BY MAX(created_at) DESC"
            )
            cur.execute(query)
            rows = cur.fetchall()
        finally:
            conn.close()

        sessions = []
        for session_id, start_at, end_at, count in rows:
            sessions.append(
                {
                    "session_id": session_id,
                    "start_at": start_at,
                    "end_at": end_at,
                    "count": count,
                }
            )
        if limit is not None and limit > 0:
            return sessions[:limit]
        return sessions

    def get_session_messages(self, session_id):
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        return rows
