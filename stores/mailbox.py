from __future__ import annotations

"""SQLite-backed mailbox for multi-agent message trace.

Every send() appends one message and persists it to disk.
This makes debugging multi-agent flows transparent because you can
query the full planner/executor conversation via SQL or a helper script.

Notes:
- This store uses a SQLite file. If you previously used JSON files,
  delete or rename them before running to avoid "not a database" errors.
"""

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class MailboxMessage:
    sender: str
    recipient: str
    content: dict[str, str]
    thread_id: str
    timestamp: str


class MailboxStore:
    """Persistent mailbox used by planner/executor/user roles."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._logger = logging.getLogger("agent.mailbox")
        self._init_db()
        self._logger.info("MailboxStore initialized: path=%s", self._path)

    def _connect(self) -> sqlite3.Connection:
        """Open a new SQLite connection for a single operation."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Ensure the mailbox table exists."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mailbox_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    content TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mailbox_thread ON mailbox_messages(thread_id)"
            )

    def send(self, sender: str, recipient: str, content: dict[str, str], thread_id: str) -> None:
        """Append one message to mailbox.

        Example:
            send("planner", "executor", {"plan": "1) ..."}, thread_id)
        """
        # Timestamps are stored in UTC to keep ordering consistent.
        message = MailboxMessage(
            sender=sender,
            recipient=recipient,
            content=content,
            thread_id=thread_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        payload = json.dumps(message.content, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mailbox_messages (sender, recipient, content, thread_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message.sender, message.recipient, payload, message.thread_id, message.timestamp),
            )

        self._logger.info(
            "Mailbox message saved: thread=%s sender=%s recipient=%s content_keys=%s",
            thread_id,
            sender,
            recipient,
            list(content.keys()),
        )

    def thread_messages(self, thread_id: str) -> list[MailboxMessage]:
        """Return all messages for one conversation thread."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT sender, recipient, content, thread_id, timestamp
                FROM mailbox_messages
                WHERE thread_id = ?
                ORDER BY id ASC
                """,
                (thread_id,),
            ).fetchall()

        messages: list[MailboxMessage] = []
        for row in rows:
            try:
                content = json.loads(row["content"])
            except json.JSONDecodeError:
                content = {"raw": row["content"]}
            messages.append(
                MailboxMessage(
                    sender=row["sender"],
                    recipient=row["recipient"],
                    content=content,
                    thread_id=row["thread_id"],
                    timestamp=row["timestamp"],
                )
            )

        self._logger.debug("Mailbox thread lookup: thread=%s messages=%s", thread_id, len(messages))
        return messages
