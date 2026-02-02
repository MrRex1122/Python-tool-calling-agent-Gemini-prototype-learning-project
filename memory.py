from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MemoryEntry:
    prompt: str
    response: str


class MemoryStore:
    """Простейшее долговременное хранилище последних диалогов."""

    def __init__(self, path: str, max_entries: int = 10) -> None:
        self._path = Path(path)
        self._max_entries = max(1, max_entries)
        self._logger = logging.getLogger("agent.memory")
        self._entries = self._load()

    def _load(self) -> list[MemoryEntry]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._logger.warning("Failed to read memory file: %s", exc)
            return []
        if not isinstance(data, list):
            self._logger.warning("Memory file has invalid format")
            return []
        entries: list[MemoryEntry] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            prompt = item.get("prompt")
            response = item.get("response")
            if isinstance(prompt, str) and isinstance(response, str):
                entries.append(MemoryEntry(prompt=prompt, response=response))
        return entries

    def _save(self) -> None:
        payload = [{"prompt": entry.prompt, "response": entry.response} for entry in self._entries]
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_interaction(self, prompt: str, response: str) -> None:
        self._entries.append(MemoryEntry(prompt=prompt, response=response))
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
        self._save()

    def format_for_prompt(self) -> str:
        if not self._entries:
            return ""
        lines: list[str] = []
        for entry in self._entries:
            lines.append(f"User: {entry.prompt}")
            lines.append(f"Assistant: {entry.response}")
        return "\n".join(lines)
