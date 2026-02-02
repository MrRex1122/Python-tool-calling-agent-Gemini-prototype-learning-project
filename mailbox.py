from __future__ import annotations

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
    """Файловый mailbox для обмена сообщениями между агентами."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._logger = logging.getLogger("agent.mailbox")
        self._messages = self._load()

    def _load(self) -> list[MailboxMessage]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._logger.warning("Failed to read mailbox file: %s", exc)
            return []
        if not isinstance(data, list):
            self._logger.warning("Mailbox file has invalid format")
            return []
        messages: list[MailboxMessage] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                messages.append(MailboxMessage(**item))
            except TypeError:
                continue
        return messages

    def _save(self) -> None:
        payload = [asdict(message) for message in self._messages]
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def send(self, sender: str, recipient: str, content: dict[str, str], thread_id: str) -> None:
        message = MailboxMessage(
            sender=sender,
            recipient=recipient,
            content=content,
            thread_id=thread_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._messages.append(message)
        self._save()

    def thread_messages(self, thread_id: str) -> list[MailboxMessage]:
        return [message for message in self._messages if message.thread_id == thread_id]
