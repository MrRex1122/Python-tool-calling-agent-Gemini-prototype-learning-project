# Python Gemini Tool Agent

Небольшой агент на Gemini с tool-calling для погоды (WeatherAPI), поддерживает:
- `single` режим (один агент),
- `multi` режим (planner + executor через mailbox, теперь режим по умолчанию).

## Быстрый старт (Windows PowerShell)

```powershell
cd "D:\Python Gemini Tool\Python-Gemini-Tool-Agent"
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Открой `.env` и укажи ключи:
- `GOOGLE_API_KEY=...`
- `WEATHERAPI_KEY=...`

## Запуск CLI

```powershell
python main.py "What's the weather forecast for Tokyo?"
```

## Запуск API (FastAPI)

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Проверка:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"prompt":"What is the weather in Tokyo?"}'
```

## Быстрый smoke-тест API

```powershell
python scripts/smoke_test.py
```

Только health-check:

```powershell
python scripts/smoke_test.py --skip-chat
```

## Основные настройки (.env)

- `AGENT_MODE=multi` (`multi` по умолчанию)
- `GEMINI_MODEL=gemini-2.5-flash`
- `MAX_TURNS=5`
- `LOG_FILE=logs/agent.log`
- `MEMORY_FILE=data/memory.json`
- `MAILBOX_FILE=data/mailbox.json`

## Структура проекта

- `core/` — конфиг и сборка раннера
- `agents/` — single/multi agent логика
- `stores/` — file-store для памяти и mailbox
- `tools/` — инструменты (weather, registry)
- `api.py` — FastAPI приложение
- `main.py` — CLI запуск

## Как еще упростить тесты

1. Добавить `pytest` + автотесты для `/health` и `/chat` (с mock runner).
2. Добавить `Makefile`/`justfile` или `tasks.py` с командами: `run-api`, `run-cli`, `smoke`.
3. Добавить GitHub Actions: запуск `py_compile` + smoke-test на каждый push.
4. Добавить фикстуры с заранее сохраненными ответами WeatherAPI (чтобы тесты были стабильны и без внешней сети).
