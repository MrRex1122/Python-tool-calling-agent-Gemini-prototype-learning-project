import logging
import sys

from agent import GeminiToolAgent
from config import AppConfig
from memory import MemoryStore
from tools import ForecastTool, ToolRegistry, WeatherTool


def main() -> None:
    # Читаем настройки из переменных окружения.
    config = AppConfig.from_env()
    # Включаем файловое логирование, чтобы видеть полный трейс работы агента.
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=config.log_file,
        encoding="utf-8",
    )
    # Регистрируем все доступные инструменты, которыми модель может пользоваться.
    tool_registry = ToolRegistry(
        [
            WeatherTool(api_key=config.weatherapi_key, base_url=config.weatherapi_base_url),
            ForecastTool(api_key=config.weatherapi_key, base_url=config.weatherapi_base_url),
        ]
    )
    # Создаем агента: модель + реестр инструментов + лимит циклов tool-calling.
    memory_store = MemoryStore(
        path=config.memory_file,
        max_entries=config.memory_max_entries,
    )
    agent = GeminiToolAgent(
        model=config.model,
        tool_registry=tool_registry,
        memory_store=memory_store,
        max_turns=config.max_turns,
    )

    # Берем запрос из аргументов командной строки или используем дефолтный.
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "What is the weather like in Boston right now?"
    print(agent.run(prompt))


if __name__ == "__main__":
    main()
