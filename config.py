from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    # Параметры приложения, которые удобно централизованно хранить в одном объекте.
    model: str
    weatherapi_base_url: str
    weatherapi_key: str
    log_level: str
    log_file: str
    memory_file: str
    memory_max_entries: int
    max_turns: int = 5

    @classmethod
    def from_env(cls) -> "AppConfig":
        # Собираем конфиг из env-переменных с безопасными значениями по умолчанию.
        return cls(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            weatherapi_base_url=os.getenv("WEATHERAPI_BASE_URL", "https://api.weatherapi.com/v1"),
            weatherapi_key=os.getenv("WEATHERAPI_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("LOG_FILE", "agent.log"),
            memory_file=os.getenv("MEMORY_FILE", "memory.json"),
            memory_max_entries=int(os.getenv("MEMORY_MAX_ENTRIES", "10")),
        )
