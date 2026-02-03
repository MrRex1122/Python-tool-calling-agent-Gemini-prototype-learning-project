from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from agents.agent import GeminiToolAgent
from agents.multi_agent import MultiAgentCoordinator
from core.config import AppConfig
from stores.mailbox import MailboxStore
from stores.memory import MemoryStore
from tools import ForecastTool, ToolRegistry, WeatherTool

Runner = Callable[[str], str]


def configure_logging(config: AppConfig) -> None:
    log_path = Path(config.log_file)
    if log_path.parent != Path("."):
        log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=config.log_file,
        encoding="utf-8",
    )


def build_runner(config: AppConfig) -> tuple[Runner, str]:
    tool_registry = ToolRegistry(
        [
            WeatherTool(api_key=config.weatherapi_key, base_url=config.weatherapi_base_url),
            ForecastTool(api_key=config.weatherapi_key, base_url=config.weatherapi_base_url),
        ]
    )

    memory_store = MemoryStore(
        path=config.memory_file,
        max_entries=config.memory_max_entries,
    )

    agent_mode = config.agent_mode if config.agent_mode in {"single", "multi"} else "multi"
    if agent_mode != config.agent_mode:
        logging.getLogger("agent").warning(
            "Unknown AGENT_MODE '%s', fallback to 'multi'",
            config.agent_mode,
        )

    if agent_mode == "multi":
        mailbox = MailboxStore(path=config.mailbox_file)
        coordinator = MultiAgentCoordinator(
            model=config.model,
            planner_registry=ToolRegistry([]),
            executor_registry=tool_registry,
            mailbox=mailbox,
            max_turns=config.max_turns,
        )
        return coordinator.run, agent_mode

    agent = GeminiToolAgent(
        model=config.model,
        tool_registry=tool_registry,
        memory_store=memory_store,
        max_turns=config.max_turns,
    )
    return agent.run, agent_mode
