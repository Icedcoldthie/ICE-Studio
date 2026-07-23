from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.lock = Lock()
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(
                '''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    source TEXT NOT NULL,
                    detected_language TEXT,
                    knowledge_used TEXT,
                    rating TEXT,
                    correction TEXT
                );

                CREATE TABLE IF NOT EXISTS viewer_memory (
                    username TEXT PRIMARY KEY,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    notes TEXT DEFAULT ''
                );
                '''
            )

    def remember_viewer(self, username: str):
        with self.lock, self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO viewer_memory(username, message_count)
                VALUES (?, 1)
                ON CONFLICT(username) DO UPDATE SET
                    last_seen = CURRENT_TIMESTAMP,
                    message_count = message_count + 1
                ''',
                (username,),
            )

    def save_interaction(
        self,
        username: str,
        message: str,
        answer: str,
        source: str,
        detected_language: str = "",
        knowledge_used: str = "",
    ) -> int:
        with self.lock, self._connect() as conn:
            cur = conn.execute(
                '''
                INSERT INTO interactions
                (username, message, answer, source, detected_language, knowledge_used)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (username, message, answer, source, detected_language, knowledge_used),
            )
            return int(cur.lastrowid)

    def save_feedback(self, interaction_id: int, rating: str, correction: str):
        with self.lock, self._connect() as conn:
            conn.execute(
                '''
                UPDATE interactions
                SET rating = ?, correction = ?
                WHERE id = ?
                ''',
                (rating, correction, interaction_id),
            )

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT * FROM interactions
                ORDER BY id DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def recent_context(self, limit: int = 14) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT username, message, answer
                FROM interactions
                ORDER BY id DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
            return [dict(row) for row in reversed(rows)]

    def get_stats(self) -> dict[str, int]:
        with self._connect() as conn:
            interactions = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
            viewers = conn.execute("SELECT COUNT(*) FROM viewer_memory").fetchone()[0]
            approved = conn.execute(
                "SELECT COUNT(*) FROM interactions WHERE rating = 'good'"
            ).fetchone()[0]
        return {
            "interactions": interactions,
            "viewers": viewers,
            "approved": approved,
        }
