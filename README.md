# Python Gemini Tool Agent

A small Gemini-based weather agent with tool-calling (WeatherAPI). This repo is a teaching-friendly agent skeleton focused on clear structure, explicit control flow, and easy debugging.

**Key Features**
1. Single-agent loop with tool-calling.
2. Multi-agent planner/executor flow with a persistent mailbox trace.
3. Router mode that decides between direct and plan-execute paths.
4. SQLite-backed short-term memory for quick context.
5. FastAPI service and CLI for simple local usage.
6. Tool output schemas validated with Pydantic models.

**How It Works (Single Mode)**
1. `main.py` or `api.py` loads configuration from `.env`.
2. `core.runtime.build_runner()` builds a `GeminiToolAgent` with tool declarations.
3. The agent sends the user prompt to Gemini.
4. If Gemini requests tools, the agent executes them via `ToolRegistry`.
5. Tool results are sent back to Gemini and the loop continues until a final response.
6. The last interactions are stored in the SQLite memory database.

**How It Works (Multi Mode)**
1. `core.runtime.build_runner()` builds a `MultiAgentCoordinator` with a planner and executor.
2. The planner generates a short numbered plan and has no tools.
3. The executor follows the plan and calls tools when needed.
4. All planner/executor/user messages are appended to the SQLite mailbox database with a thread id.
5. The planner produces the final response for the user.

**How It Works (Router Mode)**
1. `core.runtime.build_runner()` builds a `RouterCoordinator`.
2. The router agent receives the user prompt and returns JSON: `{"route":"direct"|"plan","reason":"..."}`.
3. If `route=direct`, the coordinator runs a single-agent flow.
4. If `route=plan`, the coordinator runs a multi-agent planner/executor flow.
5. If routing output cannot be parsed, the router falls back to `plan` for safety.

## Quick Start (Windows PowerShell)

```powershell
cd "D:\Python Gemini Tool\Python-Gemini-Tool-Agent"
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Open `.env` and set your keys:
1. `GOOGLE_API_KEY=...`
2. `WEATHERAPI_KEY=...`

## Run Commands (Cheat Sheet)

**CLI (single run)**

```powershell
python main.py "What's the weather forecast for Tokyo?"
```

**API server**

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

**API checks**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"prompt":"What is the weather in Tokyo?"}'
```

**Mailbox viewer**

```powershell
python scripts/mailbox_view.py --list
python scripts/mailbox_view.py --thread-id <thread_id>
```

**Smoke test**

```powershell
python scripts/smoke_test.py
python scripts/smoke_test.py --skip-chat
```

**Tests**

```powershell
python -m pytest -q
```

**Task runner**

```powershell
python tasks.py test
python tasks.py lint
python tasks.py run-api
python tasks.py run-cli -- "What's the weather in Tokyo?"
```

## Run CLI

```powershell
python main.py "What's the weather forecast for Tokyo?"
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

## API Details

**GET /health**
1. Returns a small status object with current mode and model.
2. Response shape:

```json
{"status":"ok","mode":"multi","model":"gemini-2.5-flash"}
```

**POST /chat**
1. Runs the agent once and returns the final text response.
2. Request shape:

```json
{"prompt":"What is the weather in Tokyo?"}
```

3. Response shape:

```json
{"response":"...","mode":"multi"}
```

## Configuration (.env)

1. `GOOGLE_API_KEY` — required for Gemini calls.
2. `WEATHERAPI_KEY` — required for WeatherAPI tool calls.
3. `AGENT_MODE` — `single`, `multi`, or `router`.
4. `GEMINI_MODEL` — model name, default `gemini-2.5-flash`.
5. `MAX_TURNS` — maximum tool-call turns per run.
6. `LOG_LEVEL` — logging level, default `INFO`.
7. `LOG_FILE` — file path for logs, default `logs/agent.log`.
8. `MEMORY_FILE` — SQLite file path for short-term memory, default `data/memory.db`.
9. `MEMORY_MAX_ENTRIES` — number of memory entries to keep.
10. `MAILBOX_FILE` — SQLite file path for multi-agent mailbox, default `data/mailbox.db`.

Notes:
1. If you previously used JSON files for memory or mailbox, delete or rename them.
2. `core/config.py` logs warnings if keys are missing or `AGENT_MODE` is invalid.
3. Missing `GOOGLE_API_KEY` fails only when the agent runs, not at server startup.

## Router Behavior

1. The router uses Gemini with a strict JSON format.
2. Output is parsed by `agents/router.py` and normalized to `direct` or `plan`.
3. Unknown or malformed outputs default to `plan` for safer execution.
4. The direct path uses memory; the plan path uses the mailbox trace.

## Tools

**`get_current_weather`**
1. Input schema: `{"location":"City name"}`.
2. Uses WeatherAPI `current.json` endpoint.
3. Returns a normalized response with temperature, condition, wind, and location.

**`get_weather_forecast`**
1. Input schema: `{"location":"City name","days":1..3}`.
2. Uses WeatherAPI `forecast.json` endpoint.
3. Returns a normalized list of up to 3 forecast days.

**Tool Schemas**
1. Input schemas are declared in each tool's `declaration()` method.
2. Output schemas are declared via `output_schema()` and validated with Pydantic.
3. `ToolRegistry.describe()` returns both input and output schemas for all tools.

## Data Stores

**Memory Store (`data/memory.db`)**
1. Stores the last N user/assistant exchanges for single-agent context.
2. Stored in SQLite table `memory_entries`.

**Mailbox Store (`data/mailbox.db`)**
1. Stores every planner/executor/user message for multi-agent traceability.
2. Stored in SQLite table `mailbox_messages`.

## Logging

1. Logs are written to `LOG_FILE` and include a timestamp, level, and logger name.
2. Tool calls, router decisions, and mailbox writes are logged for debugging agent behavior.

## Testing

Unit tests are lightweight and do not call external APIs. They inject a fake runner into `create_app()` so tests run fast and deterministically.

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

## Project Structure

1. `core/` — config and runtime composition.
2. `agents/` — single-agent loop, router, and multi-agent coordinator.
3. `stores/` — SQLite-backed memory and mailbox.
4. `tools/` — tool registry and WeatherAPI tools.
5. `api.py` — FastAPI application entrypoint.
6. `main.py` — CLI entrypoint.
7. `tasks.py` — small command runner.
8. `tests/` — pytest-based unit tests.
9. `scripts/mailbox_view.py` — CLI viewer for mailbox threads.

## Troubleshooting

1. `GOOGLE_API_KEY` missing: Gemini calls will fail at runtime with an explicit error.
2. `WEATHERAPI_KEY` missing: weather tools will fail with a clear error.
3. Router output malformed: router falls back to `plan` and logs the decision.
4. Old JSON files: delete or rename `data/memory.json` or `data/mailbox.json` if present.
5. Network issues: WeatherAPI requests time out after 10 seconds and return an error message.

## Redis Note (Optional)

Redis is not required for this small project. It becomes useful when you want:
1. Fast short-term memory storage (last N messages).
2. Tool-call caching with TTL.
3. Session storage or rate limiting.

For long-term history, SQL (SQLite/Postgres) is still the better default.
