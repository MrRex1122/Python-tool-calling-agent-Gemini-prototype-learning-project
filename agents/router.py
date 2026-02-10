from __future__ import annotations

"""Router agent that selects which execution path to use.

This module introduces a lightweight routing step before running the agent:
1) The router inspects the user prompt.
2) It decides between:
   - "direct": run a single agent (fast path).
   - "plan": run a planner/executor multi-agent flow (slow but thorough).
3) The coordinator runs the chosen path and returns the final response.

The router itself uses Gemini with a constrained JSON output to keep
its decision machine-readable and easy to debug.
"""

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from agents.agent import GeminiToolAgent
from tools.registry import ToolRegistry


@dataclass(frozen=True)
class RouteDecision:
    """Normalized routing decision produced by the router.

    Fields:
    - route: "direct" or "plan"
    - reason: short explanation for logging/debugging
    - raw: raw model response for traceability
    """

    route: str
    reason: str
    raw: str


class RunnerProtocol(Protocol):
    """Simple protocol for any runner that exposes .run(prompt)."""

    def run(self, prompt: str) -> str:
        ...


def _normalize_route(value: str | None) -> str | None:
    """Normalize raw route value into a known route or None."""
    if not value:
        return None
    cleaned = value.strip().lower()
    mapping = {
        "direct": "direct",
        "single": "direct",
        "fast": "direct",
        "plan": "plan",
        "planner": "plan",
        "multi": "plan",
        "plan-execute": "plan",
        "plan_execute": "plan",
    }
    return mapping.get(cleaned)


def _extract_json(text: str) -> str | None:
    """Best-effort extraction of a JSON object from model output."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def parse_router_response(text: str) -> RouteDecision | None:
    """Parse router model output into a RouteDecision.

    The router is instructed to return JSON, but we still tolerate noisy output.
    If parsing fails, we return None and the caller chooses a safe fallback.
    """
    if not text:
        return None

    raw = text.strip()

    snippet = _extract_json(raw)
    if snippet:
        try:
            data = json.loads(snippet)
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict):
            route = _normalize_route(str(data.get("route", "")))
            reason = str(data.get("reason", "")).strip() or "No reason provided."
            if route:
                return RouteDecision(route=route, reason=reason, raw=raw)

    # Fallback keyword detection for non-JSON responses.
    lowered = raw.lower()
    if "direct" in lowered:
        return RouteDecision(route="direct", reason="Fallback: matched keyword 'direct'.", raw=raw)
    if "plan" in lowered or "planner" in lowered or "multi" in lowered:
        return RouteDecision(route="plan", reason="Fallback: matched keyword 'plan'.", raw=raw)

    return None


class RouterAgent:
    """LLM-backed router that decides direct vs plan execution."""

    def __init__(self, model: str, max_turns: int = 1) -> None:
        # Router should not use tools. It only decides on the execution path.
        self._agent = GeminiToolAgent(
            model=model,
            tool_registry=ToolRegistry([]),
            system_prompt=(
                "You are a router. Decide how to handle the user request. "
                "Return JSON only: {\"route\": \"direct\"|\"plan\", "
                "\"reason\": \"short explanation\"}. "
                "Use 'direct' for simple questions that do not need tools or multi-step planning. "
                "Use 'plan' when tools, external data, or multi-step reasoning are likely needed."
            ),
            max_turns=max(1, max_turns),
        )
        self._logger = logging.getLogger("agent.router")

    def decide(self, prompt: str) -> RouteDecision:
        """Return a normalized routing decision for a user prompt."""
        raw = self._agent.run(
            "User request:\n"
            f"{prompt}\n\n"
            "Return routing JSON only."
        )
        decision = parse_router_response(raw)
        if decision is None:
            # Safe default: fall back to plan for thorough execution.
            decision = RouteDecision(
                route="plan",
                reason="Fallback: unable to parse router response.",
                raw=raw,
            )
        self._logger.info("Router decision: route=%s reason=%s", decision.route, decision.reason)
        return decision


class RouterCoordinator:
    """Coordinator that routes a request to direct or plan-execute paths."""

    def __init__(
        self,
        router: RouterAgent,
        direct_agent: RunnerProtocol,
        plan_agent: RunnerProtocol,
    ) -> None:
        self._router = router
        self._direct_agent = direct_agent
        self._plan_agent = plan_agent
        self._logger = logging.getLogger("agent.router.coordinator")

    def run(self, prompt: str) -> str:
        """Route a prompt and return the final response."""
        decision = self._router.decide(prompt)

        if decision.route == "direct":
            self._logger.info("Routing to direct agent")
            return self._direct_agent.run(prompt)

        self._logger.info("Routing to plan-execute coordinator")
        return self._plan_agent.run(prompt)
