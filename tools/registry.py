from __future__ import annotations

"""Tool registry used by the agent.

Responsibilities:
1) Expose tool declarations to Gemini.
2) Route function calls by tool name.
3) Return uniform result/error payloads.

This keeps the agent loop simple and predictable.
"""

import logging
from typing import Any, Iterable, Protocol

from google.genai import types


class ToolProtocol(Protocol):
    # Minimal contract every tool must implement.
    # Example tool class: WeatherTool in tools/weather.py
    name: str

    def declaration(self) -> types.FunctionDeclaration:
        ...

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        ...


class ToolRegistry:
    def __init__(self, tools: Iterable[ToolProtocol]) -> None:
        self._logger = logging.getLogger("agent.tools.registry")
        # Map by tool name for O(1) lookup when model requests function call.
        self._tools = {tool.name: tool for tool in tools}
        self._logger.info("ToolRegistry initialized with tools=%s", list(self._tools.keys()))

    def build_tools(self) -> list[types.Tool]:
        """Convert python tools into Gemini declarations list.

        Gemini expects function declarations (name/schema/description), not python callables.
        """
        declarations = [tool.declaration() for tool in self._tools.values()]
        self._logger.debug("Built %s tool declarations", len(declarations))
        return [types.Tool(function_declarations=declarations)]

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute one tool call and normalize output shape.

        Success shape:
            {"result": {...}}
        Failure shape:
            {"error": "..."}
        """
        tool = self._tools.get(name)
        if tool is None:
            self._logger.warning("Unknown tool requested: %s", name)
            return {"error": f"Unknown tool: {name}"}

        try:
            result = tool.execute(**args)
            self._logger.debug("Tool executed successfully: %s", name)
            return {"result": result}
        except Exception as exc:
            # Keep error text short and safe to send back to model.
            self._logger.exception("Tool execution failed: %s", name)
            return {"error": str(exc)}
