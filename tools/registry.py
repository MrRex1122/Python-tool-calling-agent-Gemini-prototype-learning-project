from __future__ import annotations

from typing import Any, Iterable, Protocol

from google.genai import types


class ToolProtocol(Protocol):
    # Базовый контракт для любого инструмента.
    name: str

    def declaration(self) -> types.FunctionDeclaration:
        ...

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        ...


class ToolRegistry:
    def __init__(self, tools: Iterable[ToolProtocol]) -> None:
        # Храним инструменты по имени, чтобы быстро находить по function-call.
        self._tools = {tool.name: tool for tool in tools}

    def build_tools(self) -> list[types.Tool]:
        # Gemini получает только декларации функций (схемы аргументов и описания).
        declarations = [tool.declaration() for tool in self._tools.values()]
        return [types.Tool(function_declarations=declarations)]

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"Unknown tool: {name}"}

        try:
            return {"result": tool.execute(**args)}
        except Exception as exc:
            return {"error": str(exc)}
