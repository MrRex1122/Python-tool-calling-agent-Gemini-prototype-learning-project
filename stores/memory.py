from __future__ import annotations

"""SQLite-backed memory store.

Purpose:
1) Keep last N user/assistant exchanges.
2) Provide a compact context block for the next prompt.

Notes:
- This store uses a SQLite file. If you previously used JSON files,
  delete or rename them before running to avoid "not a database" errors.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class MemoryEntry:
    prompt: str
    response: str
    created_at: str


class MemoryStore:
    """Persistent short-term chat memory using SQLite.

    The store keeps only the last N entries to avoid unbounded growth.
    """

    def __init__(self, path: str, max_entries: int = 10) -> None:
        self._path = Path(path)
        self._max_entries = max(1, max_entries)
        self._logger = logging.getLogger("agent.memory")
        self._init_db()
        self._logger.info(
            "MemoryStore initialized: path=%s max_entries=%s",
            self._path,
            self._max_entries,
        )

    def _connect(self) -> sqlite3.Connection:
        """Open a new SQLite connection for a single operation."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Ensure the memory table exists."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_entries(created_at)"
            )

    def add_interaction(self, prompt: str, response: str) -> None:
        """Append a new interaction and keep only last N entries."""
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO memory_entries (prompt, response, created_at) VALUES (?, ?, ?)",
                (prompt, response, created_at),
            )
            conn.execute(
                """
                DELETE FROM memory_entries
                WHERE id NOT IN (
                    SELECT id FROM memory_entries ORDER BY id DESC LIMIT ?
                )
                """,
                (self._max_entries,),
            )
        self._logger.debug("Memory entry saved at %s", created_at)

    def format_for_prompt(self) -> str:
        """Return memory in plain text block ready for LLM prompt injection.

        Example output:
            User: weather in Berlin
            Assistant: 12C, light rain.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT prompt, response, created_at
                FROM memory_entries
                ORDER BY id DESC
                LIMIT ?
                """,
                (self._max_entries,),
            ).fetchall()

        if not rows:
            return ""

        entries = [
            MemoryEntry(
                prompt=row["prompt"],
                response=row["response"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

        lines: list[str] = []
        for entry in reversed(entries):
            lines.append(f"User: {entry.prompt}")
            lines.append(f"Assistant: {entry.response}")

        formatted = "\n".join(lines)
        self._logger.debug("Formatted memory context: %s chars", len(formatted))
        return formatted
