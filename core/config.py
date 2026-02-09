from __future__ import annotations

"""Application configuration bootstrap.

Why this module exists:
- Keep all env variables in one place.
- Provide safe defaults for local development.
- Avoid hardcoding keys or file paths in business logic.

Example .env:
    GOOGLE_API_KEY=your_google_api_key
    WEATHERAPI_KEY=your_weatherapi_key
    AGENT_MODE=multi
"""

import logging
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    # Automatically load .env (if present) for local runs.
    # Shell variables still have priority by default.
    load_dotenv()

LOGGER = logging.getLogger("agent.config")


def _read_int_env(name: str, default: int) -> int:
    """Read integer env var with fallback + warning on invalid values.

    Example:
    - MAX_TURNS=8   -> 8
    - MAX_TURNS=abc -> warning + default
    """
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        LOGGER.warning("Invalid integer %s=%r. Using default=%s.", name, raw_value, default)
        return default


@dataclass(frozen=True)
class AppConfig:
    """Immutable runtime configuration used by CLI and API entrypoints."""

    # LLM and external API settings.
    model: str
    weatherapi_base_url: str
    weatherapi_key: str

    # Logging settings.
    log_level: str
    log_file: str

    # Local state files.
    memory_file: str
    memory_max_entries: int
    mailbox_file: str

    # Agent behavior.
    agent_mode: str
    max_turns: int = 5

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build configuration from environment variables.

        Security note:
        - Keep secrets in .env / secret manager.
        - Do not commit .env.
        """
        config = cls(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            weatherapi_base_url=os.getenv("WEATHERAPI_BASE_URL", "https://api.weatherapi.com/v1"),
            weatherapi_key=os.getenv("WEATHERAPI_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("LOG_FILE", "logs/agent.log"),
            memory_file=os.getenv("MEMORY_FILE", "data/memory.json"),
            memory_max_entries=_read_int_env("MEMORY_MAX_ENTRIES", 10),
            mailbox_file=os.getenv("MAILBOX_FILE", "data/mailbox.json"),
            agent_mode=os.getenv("AGENT_MODE", "multi").lower(),
            max_turns=_read_int_env("MAX_TURNS", 5),
        )

        if not os.getenv("GOOGLE_API_KEY"):
            LOGGER.warning("GOOGLE_API_KEY is not set. Gemini calls will fail.")
        if not config.weatherapi_key:
            LOGGER.warning("WEATHERAPI_KEY is not set. Weather tools will fail.")
        if config.agent_mode not in {"single", "multi"}:
            LOGGER.warning(
                "Unknown AGENT_MODE '%s'. Runtime will fall back to 'multi'.",
                config.agent_mode,
            )

        # Never log secrets (API keys). Log only safe metadata.
        LOGGER.debug(
            "Config loaded: model=%s mode=%s max_turns=%s log_file=%s memory_file=%s mailbox_file=%s",
            config.model,
            config.agent_mode,
            config.max_turns,
            config.log_file,
            config.memory_file,
            config.mailbox_file,
        )
        return config
