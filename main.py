import sys

from core.config import AppConfig
from core.runtime import build_runner, configure_logging


def main() -> None:
    config = AppConfig.from_env()
    configure_logging(config)
    runner, _ = build_runner(config)

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "What is the weather like in Boston right now?"
    print(runner(prompt))


if __name__ == "__main__":
    main()
