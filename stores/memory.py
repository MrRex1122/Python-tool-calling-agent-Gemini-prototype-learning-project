from __future__ import annotations

"""Simple file-based memory store.

Purpose:
- Keep last N user/assistant exchanges.
- Provide a compact context block for the next prompt.

Example stored item:
    {"prompt": "weather in Tokyo", "response": "It is 8C and cloudy."}
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MemoryEntry:
    prompt: str
    response: str


class MemoryStore:
    """Persistent short-term chat memory."""

    def __init__(self, path: str, max_entries: int = 10) -> None:
        self._path = Path(path)
        self._max_entries = max(1, max_entries)
        self._logger = logging.getLogger("agent.memory")
        self._entries = self._load()
        self._logger.info(
            "MemoryStore initialized: path=%s entries=%s max_entries=%s",
            self._path,
            len(self._entries),
            self._max_entries,
        )

    def _load(self) -> list[MemoryEntry]:
        """Load entries from disk. Invalid rows are skipped."""
        if not self._path.exists():
            self._logger.debug("Memory file does not exist yet: %s", self._path)
            return []

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._logger.warning("Failed to read memory file %s: %s", self._path, exc)
            return []

        if not isinstance(data, list):
            self._logger.warning("Memory file has invalid format (expected list): %s", self._path)
            return []

        entries: list[MemoryEntry] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            prompt = item.get("prompt")
            response = item.get("response")
            if isinstance(prompt, str) and isinstance(response, str):
                entries.append(MemoryEntry(prompt=prompt, response=response))

        self._logger.debug("Loaded %s valid memory entries from %s", len(entries), self._path)
        return entries

    def _save(self) -> None:
        """Write memory entries to disk with pretty JSON for easy inspection."""
        payload = [{"prompt": entry.prompt, "response": entry.response} for entry in self._entries]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._logger.debug("Saved %s memory entries to %s", len(self._entries), self._path)

    def add_interaction(self, prompt: str, response: str) -> None:
        """Append a new interaction and keep only last N entries."""
        self._entries.append(MemoryEntry(prompt=prompt, response=response))
        if len(self._entries) > self._max_entries:
            dropped = len(self._entries) - self._max_entries
            self._entries = self._entries[-self._max_entries :]
            self._logger.debug("Memory trimmed by %s old entries", dropped)
        self._save()

    def format_for_prompt(self) -> str:
        """Return memory in plain text block ready for LLM prompt injection.

        Example output:
            User: weather in Berlin
            Assistant: 12C, light rain.
        """
        if not self._entries:
            return ""
        lines: list[str] = []
        for entry in self._entries:
            lines.append(f"User: {entry.prompt}")
            lines.append(f"Assistant: {entry.response}")
        formatted = "\n".join(lines)
        self._logger.debug("Formatted memory context: %s chars", len(formatted))
        return formatted
