from __future__ import annotations

import logging
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from core.config import AppConfig
from core.runtime import build_runner, configure_logging


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str
    mode: str


class HealthResponse(BaseModel):
    status: str
    mode: str
    model: str


def create_app() -> FastAPI:
    config = AppConfig.from_env()
    configure_logging(config)
    runner, agent_mode = build_runner(config)
    logger = logging.getLogger("agent.api")

    app = FastAPI(
        title="Gemini Tool Agent API",
        version="1.0.0",
    )
    app.state.runner = runner
    app.state.runner_lock = Lock()
    app.state.agent_mode = agent_mode
    app.state.model = config.model

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", mode=app.state.agent_mode, model=app.state.model)

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        prompt = request.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=422, detail="Prompt must not be empty.")

        def _run_agent() -> str:
            # File-based memory/mailbox stores are mutable, so keep execution serialized.
            with app.state.runner_lock:
                return app.state.runner(prompt)

        try:
            response_text = await run_in_threadpool(_run_agent)
        except Exception as exc:
            logger.exception("Chat request failed")
            raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc

        return ChatResponse(response=response_text, mode=app.state.agent_mode)

    return app


app = create_app()
