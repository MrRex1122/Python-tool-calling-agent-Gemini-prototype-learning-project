from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types

from memory import MemoryStore
from tools.registry import ToolRegistry


class GeminiToolAgent:
    """Агент, который делает цикл: LLM -> tool call -> tool result -> LLM."""

    def __init__(
        self,
        model: str,
        tool_registry: ToolRegistry,
        memory_store: MemoryStore | None = None,
        max_turns: int = 5,
    ) -> None:
        self._client = genai.Client()
        self._model = model
        self._tool_registry = tool_registry
        self._memory_store = memory_store
        self._max_turns = max_turns
        self._logger = logging.getLogger("agent")

    def run(self, prompt: str) -> str:
        # Передаем модели описание всех инструментов.
        config = types.GenerateContentConfig(tools=self._tool_registry.build_tools())
        contents: list[types.Content] = []
        memory_context = self._memory_store.format_for_prompt() if self._memory_store else ""
        if memory_context:
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text="Previous conversation context:\n" + memory_context
                        )
                    ],
                )
            )
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

        for _ in range(self._max_turns):
            self._logger.info("LLM request: model=%s prompt=%s", self._model, prompt)
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

            # Если function_calls пустой — модель уже дала финальный ответ.
            if not response.function_calls:
                self._logger.info("LLM response: no tool calls")
                final_response = response.text or ""
                if self._memory_store:
                    self._memory_store.add_interaction(prompt, final_response)
                return final_response

            self._logger.info("LLM response: %s tool call(s)", len(response.function_calls))
            function_call_content = response.candidates[0].content
            function_response_parts: list[types.Part] = []

            for call in response.function_calls:
                name = self._get_call_name(call)
                args = self._get_call_args(call)
                self._logger.info("Tool call: name=%s args=%s", name, args)

                # Выполняем tool в Python-коде и отправляем результат обратно в модель.
                tool_response = self._tool_registry.execute(name or "unknown", args)
                self._logger.info("Tool response: name=%s keys=%s", name, list(tool_response.keys()))
                function_response_parts.append(
                    types.Part.from_function_response(name=name or "unknown", response=tool_response)
                )

            # Добавляем в историю и сам запрос инструмента, и его ответ.
            contents.append(function_call_content)
            contents.append(types.Content(role="tool", parts=function_response_parts))

        final_response = "Stopped after too many tool-call turns."
        if self._memory_store:
            self._memory_store.add_interaction(prompt, final_response)
        return final_response

    @staticmethod
    def _get_call_name(call: Any) -> str | None:
        if hasattr(call, "name") and call.name:
            return call.name
        if hasattr(call, "function_call") and getattr(call.function_call, "name", None):
            return call.function_call.name
        return None

    @staticmethod
    def _get_call_args(call: Any) -> dict[str, Any]:
        if hasattr(call, "args") and call.args is not None:
            return call.args
        if hasattr(call, "function_call") and getattr(call.function_call, "args", None) is not None:
            return call.function_call.args
        return {}
