from __future__ import annotations

"""FastAPI entrypoint for the agent.

Run locally:
    python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload

Request example:
    POST /chat
    {"prompt": "What is the weather in Tokyo?"}
"""

import logging
from collections.abc import Callable
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.config import AppConfig
from core.runtime import build_runner, configure_logging


class ChatRequest(BaseModel):
    # Keep request shape minimal for learning and debugging.
    prompt: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str
    mode: str


class HealthResponse(BaseModel):
    status: str
    mode: str
    model: str


def create_app(
    runner: Callable[[str], str] | None = None,
    agent_mode: str | None = None,
    model: str | None = None,
) -> FastAPI:
    """Create FastAPI app.

    Optional runner injection keeps tests fast and independent of external APIs.
    """
    logger = logging.getLogger("agent.api")

    if runner is None:
        # Build runtime once during app startup.
        config = AppConfig.from_env()
        configure_logging(config)
        runner, agent_mode = build_runner(config)
        model = config.model
    else:
        # Tests or custom wiring can inject runner + metadata.
        if agent_mode is None:
            agent_mode = "custom"
        if model is None:
            model = "custom"

    app = FastAPI(
        title="Gemini Tool Agent API",
        version="1.0.0",
    )

    # `app.state` keeps shared runtime objects.
    app.state.runner = runner
    app.state.runner_lock = Lock()
    app.state.agent_mode = agent_mode
    app.state.model = model

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        # Useful for monitoring and quick smoke checks.
        return HealthResponse(status="ok", mode=app.state.agent_mode, model=app.state.model)

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        prompt = request.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=422, detail="Prompt must not be empty.")

        logger.info("/chat request received: prompt_chars=%s mode=%s", len(prompt), app.state.agent_mode)

        def _run_agent() -> str:
            # File-based memory/mailbox stores are mutable; serialize runs.
            # This prevents race conditions when multiple requests arrive at once.
            with app.state.runner_lock:
                return app.state.runner(prompt)

        try:
            # Run blocking agent code in threadpool to keep event loop responsive.
            response_text = await run_in_threadpool(_run_agent)
        except Exception as exc:
            logger.exception("Chat request failed")
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc

        logger.info("/chat request completed: response_chars=%s", len(response_text))
        return ChatResponse(response=response_text, mode=app.state.agent_mode)

    return app


# ASGI app instance used by uvicorn.
app = create_app()
