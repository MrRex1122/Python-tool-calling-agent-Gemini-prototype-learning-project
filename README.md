# Python Gemini Tool Agent

A small Gemini-based weather agent with tool-calling (WeatherAPI).  
It supports:
- `single` mode (one agent),
- `multi` mode (planner + executor via mailbox, default mode).

## Quick Start (Windows PowerShell)

```powershell
cd "D:\Python Gemini Tool\Python-Gemini-Tool-Agent"
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Open `.env` and set your keys:
- `GOOGLE_API_KEY=...`
- `WEATHERAPI_KEY=...`

## Run CLI

```powershell
python main.py "What's the weather forecast for Tokyo?"
```

## Tasks (Optional)

```powershell
python tasks.py test
python tasks.py lint
python tasks.py run-api
python tasks.py run-cli -- "What's the weather in Tokyo?"
```

## Run API (FastAPI)

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Check endpoints:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"prompt":"What is the weather in Tokyo?"}'
```

## Testing

Unit tests are lightweight and do not call external APIs.
They inject a fake runner into `create_app()` so tests run fast and deterministically.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Development Tasks

`tasks.py` provides a minimal task runner to keep common commands consistent:

```powershell
python tasks.py test
python tasks.py lint
python tasks.py run-api
python tasks.py run-cli -- "What's the weather in Tokyo?"
```

## Runtime Notes

- `create_app()` supports dependency injection for tests or custom wiring:
  - `create_app(runner=..., agent_mode=..., model=...)`
  - When not provided, runtime is built from `.env` and logging is configured.
- Gemini client initialization is lazy. This avoids hard failures on startup
  when `GOOGLE_API_KEY` is not set (it will fail only when the agent runs).
- `core/config.py` logs warnings if `GOOGLE_API_KEY` or `WEATHERAPI_KEY` are missing
  and if `AGENT_MODE` is invalid (fallback to `multi`).

## Quick API Smoke Test

```powershell
python scripts/smoke_test.py
```

Health check only:

```powershell
python scripts/smoke_test.py --skip-chat
```

## Main Settings (.env)

- `AGENT_MODE=multi` (`multi` is the default)
- `GEMINI_MODEL=gemini-2.5-flash`
- `MAX_TURNS=5`
- `LOG_FILE=logs/agent.log`
- `MEMORY_FILE=data/memory.json`
- `MAILBOX_FILE=data/mailbox.json`

## Project Structure

- `core/` - config and runner composition
- `agents/` - single/multi-agent logic
- `stores/` - file-based memory and mailbox stores
- `tools/` - tools (`weather`, `registry`)
- `api.py` - FastAPI app entrypoint
- `main.py` - CLI entrypoint

## Ideas to Simplify Testing Further

1. Add `pytest` tests for `/health` and `/chat` (with mocked runner).
2. Add `Makefile` / `justfile` / `tasks.py` commands (`run-api`, `run-cli`, `smoke`).
3. Add GitHub Actions for `py_compile` + smoke test on each push.
4. Add WeatherAPI fixtures/mocks to make tests stable and network-independent.
