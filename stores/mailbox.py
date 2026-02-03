from __future__ import annotations

"""File-based mailbox for multi-agent message trace.

Every send() appends one message and persists it to disk.
This makes debugging multi-agent flows very transparent.
"""

import json
import logging
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
        self._messages = self._load()
        self._logger.info("MailboxStore initialized: path=%s messages=%s", self._path, len(self._messages))

    def _load(self) -> list[MailboxMessage]:
        """Load mailbox messages from disk. Invalid rows are ignored."""
        if not self._path.exists():
            self._logger.debug("Mailbox file does not exist yet: %s", self._path)
            return []

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._logger.warning("Failed to read mailbox file %s: %s", self._path, exc)
            return []

        if not isinstance(data, list):
            self._logger.warning("Mailbox file has invalid format (expected list): %s", self._path)
            return []

        messages: list[MailboxMessage] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                messages.append(MailboxMessage(**item))
            except TypeError:
                # Skip malformed message rows instead of failing whole load.
                continue

        self._logger.debug("Loaded %s mailbox messages from %s", len(messages), self._path)
        return messages

    def _save(self) -> None:
        """Persist full mailbox to disk in readable JSON format."""
        payload = [asdict(message) for message in self._messages]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._logger.debug("Saved %s mailbox messages to %s", len(self._messages), self._path)

    def send(self, sender: str, recipient: str, content: dict[str, str], thread_id: str) -> None:
        """Append one message to mailbox.

        Example:
            send("planner", "executor", {"plan": "1) ..."}, thread_id)
        """
        message = MailboxMessage(
            sender=sender,
            recipient=recipient,
            content=content,
            thread_id=thread_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._messages.append(message)
        self._save()
        self._logger.info(
            "Mailbox message saved: thread=%s sender=%s recipient=%s content_keys=%s",
            thread_id,
            sender,
            recipient,
            list(content.keys()),
        )

    def thread_messages(self, thread_id: str) -> list[MailboxMessage]:
        """Return all messages for one conversation thread."""
        messages = [message for message in self._messages if message.thread_id == thread_id]
        self._logger.debug("Mailbox thread lookup: thread=%s messages=%s", thread_id, len(messages))
        return messages
