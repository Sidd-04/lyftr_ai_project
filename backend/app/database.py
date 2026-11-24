import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/app.db")

def get_db_path() -> str:
    url = DATABASE_URL
    if url.startswith("sqlite:////"):
        return "/" + url[len("sqlite:////"):]
    elif url.startswith("sqlite:///"):
        return url[len("sqlite:///"): ]
    return url

def get_db_connection() -> sqlite3.Connection:
    path = get_db_path()
    # Ensure directory exists
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages (session_id);")
    finally:
        conn.close()

def save_message(session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
    conn = get_db_connection()
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        meta_str = json.dumps(metadata) if metadata is not None else None
        with conn:
            cursor = conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, meta_str, now_iso)
            )
            return cursor.lastrowid
    finally:
        conn.close()

def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT role, content, metadata FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            item = {
                "role": r["role"],
                "content": r["content"]
            }
            if r["role"] == "assistant" and r["metadata"]:
                item["metadata"] = json.loads(r["metadata"])
            result.append(item)
        return result
    finally:
        conn.close()

def session_exists(session_id: str) -> bool:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM messages WHERE session_id = ? LIMIT 1",
            (session_id,)
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()
