from __future__ import annotations

"""Runtime composition helpers.

This module wires together:
- tools,
- stores,
- agent mode (single / multi),
- logging.

Keeping this in one place avoids duplicate setup code in `main.py` and `api.py`.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from agents.agent import GeminiToolAgent
from agents.multi_agent import MultiAgentCoordinator
from core.config import AppConfig
from stores.mailbox import MailboxStore
from stores.memory import MemoryStore
from tools import ForecastTool, ToolRegistry, WeatherTool

# Runner signature used by both CLI and API layers.
# Example call: `response = runner("Weather in Tokyo")`.
Runner = Callable[[str], str]


def configure_logging(config: AppConfig) -> None:
    """Initialize file logging according to AppConfig."""
    log_path = Path(config.log_file)

    # Ensure target folder exists (for defaults this is `logs/`).
    # Example: logs/agent.log -> create logs/ if missing.
    if log_path.parent != Path("."):
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # `basicConfig` is enough for this learning project.
    # For larger systems consider structured JSON logging.
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=config.log_file,
        encoding="utf-8",
    )
    logging.getLogger("agent.runtime").info(
        "Logging configured: file=%s level=%s",
        config.log_file,
        config.log_level,
    )


def _resolve_agent_mode(raw_mode: str) -> str:
    """Normalize mode and keep behavior predictable for invalid values."""
    return raw_mode if raw_mode in {"single", "multi"} else "multi"


def build_runner(config: AppConfig) -> tuple[Runner, str]:
    """Build callable runner based on config.

    Returns:
        tuple(runner_function, resolved_mode)

    Example:
        runner, mode = build_runner(config)
        text = runner("What's the weather in Tokyo?")
    """
    logger = logging.getLogger("agent.runtime")
    logger.info("Building runner for requested mode=%s", config.agent_mode)

    # Register model tools once and reuse.
    # Current tools: current weather + forecast.
    tool_registry = ToolRegistry(
        [
            WeatherTool(api_key=config.weatherapi_key, base_url=config.weatherapi_base_url),
            ForecastTool(api_key=config.weatherapi_key, base_url=config.weatherapi_base_url),
        ]
    )
    logger.info("Tool registry initialized")

    # Memory is used by single-agent mode to provide short chat history.
    memory_store = MemoryStore(
        path=config.memory_file,
        max_entries=config.memory_max_entries,
    )

    agent_mode = _resolve_agent_mode(config.agent_mode)
    if agent_mode != config.agent_mode:
        logger.warning("Unknown AGENT_MODE '%s'. Fallback to '%s'.", config.agent_mode, agent_mode)

    if agent_mode == "multi":
        # Multi mode uses mailbox to track planner/executor message exchange.
        mailbox = MailboxStore(path=config.mailbox_file)
        coordinator = MultiAgentCoordinator(
            model=config.model,
            planner_registry=ToolRegistry([]),
            executor_registry=tool_registry,
            mailbox=mailbox,
            max_turns=config.max_turns,
        )
        logger.info("Runner created: multi-agent coordinator")
        return coordinator.run, agent_mode

    # Single mode: one agent handles prompt + tool calls directly.
    agent = GeminiToolAgent(
        model=config.model,
        tool_registry=tool_registry,
        memory_store=memory_store,
        max_turns=config.max_turns,
    )
    logger.info("Runner created: single agent")
    return agent.run, agent_mode
