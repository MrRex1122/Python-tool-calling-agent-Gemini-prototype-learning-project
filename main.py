"""CLI entrypoint for the agent.

What this file does:
1) Load configuration from the environment.
2) Configure file logging.
3) Build the runtime runner (single or multi).
4) Read a prompt from CLI arguments.
5) Execute one agent run and print the response.

Usage examples:
    python main.py "What's the weather forecast for Tokyo?"
    python main.py
"""

import logging
import sys

from core.config import AppConfig
from core.runtime import build_runner, configure_logging


def main() -> None:
    # 1) Load env-based config (model, API keys, memory paths, etc).
    config = AppConfig.from_env()

    # 2) Configure file logging before any agent work starts.
    configure_logging(config)
    logger = logging.getLogger("agent.cli")

    # 3) Build runner (single or multi based on config).
    runner, resolved_mode = build_runner(config)
    logger.info("CLI started with mode=%s", resolved_mode)

    # 4) Read prompt from CLI args; fallback to a safe default.
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        # Default demo prompt keeps a no-arg run useful.
        prompt = "What is the weather like in Boston right now?"

    logger.info("CLI prompt: %s", prompt)
    print(runner(prompt))


if __name__ == "__main__":
    main()
