"""CLI entrypoint.

Examples:
    python main.py "What's the weather forecast for Tokyo?"
    python main.py
"""

import logging
import sys

from core.config import AppConfig
from core.runtime import build_runner, configure_logging


def main() -> None:
    # 1) Load env-based config.
    config = AppConfig.from_env()

    # 2) Configure file logging.
    configure_logging(config)
    logger = logging.getLogger("agent.cli")

    # 3) Build runner (single or multi based on config).
    runner, resolved_mode = build_runner(config)
    logger.info("CLI started with mode=%s", resolved_mode)

    # 4) Read prompt from CLI args.
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        # Default demo prompt useful for first run.
        prompt = "What is the weather like in Boston right now?"

    logger.info("CLI prompt: %s", prompt)
    print(runner(prompt))


if __name__ == "__main__":
    main()
