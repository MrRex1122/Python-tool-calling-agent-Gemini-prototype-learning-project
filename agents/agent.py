from __future__ import annotations

"""Single-agent tool-calling loop.

High-level flow:
1) Send user prompt (and optional memory) to Gemini.
2) If model requests tool calls -> execute tools.
3) Send tool results back to Gemini.
4) Repeat until final text answer or max turns reached.
"""

import logging
from typing import Any

from google import genai
from google.genai import types

from stores.memory import MemoryStore
from tools.registry import ToolRegistry


class GeminiToolAgent:
    """Agent that orchestrates LLM <-> tools interaction."""

    def __init__(
        self,
        model: str,
        tool_registry: ToolRegistry,
        system_prompt: str | None = None,
        memory_store: MemoryStore | None = None,
        max_turns: int = 5,
    ) -> None:
        # Gemini client reads credentials from environment (GOOGLE_API_KEY etc).
        self._client = genai.Client()
        self._model = model
        self._tool_registry = tool_registry
        self._system_prompt = system_prompt
        self._memory_store = memory_store
        self._max_turns = max(1, max_turns)
        self._logger = logging.getLogger("agent")

    def run(self, prompt: str) -> str:
        """Run one prompt through the tool-calling loop and return final text.

        Example:
            agent.run("What is the weather in Tokyo?")
        """
        prompt = prompt.strip()
        if not prompt:
            self._logger.warning("Empty prompt received; returning guidance message")
            return "Prompt is empty. Please provide a question."

        self._logger.info("Agent run started: model=%s prompt=%s", self._model, self._preview(prompt))

        # Tools are declared once in config.
        # If system prompt is provided, pass it as `system_instruction`.
        config_kwargs: dict[str, Any] = {"tools": self._tool_registry.build_tools()}
        if self._system_prompt:
            config_kwargs["system_instruction"] = self._system_prompt
        config = types.GenerateContentConfig(**config_kwargs)

        contents: list[types.Content] = []

        # Optional memory context. This helps single-agent mode keep short history.
        memory_context = self._memory_store.format_for_prompt() if self._memory_store else ""
        if memory_context:
            self._logger.debug("Memory context attached: %s chars", len(memory_context))
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="Previous conversation context:\n" + memory_context)],
                )
            )

        # Current user request.
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))

        # Core loop: model -> optional tool calls -> model.
        for turn_number in range(1, self._max_turns + 1):
            self._logger.info("LLM turn %s/%s", turn_number, self._max_turns)
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

            # No function calls means model returned final text response.
            if not response.function_calls:
                final_response = response.text or ""
                self._logger.info(
                    "LLM final response received: %s chars preview=%s",
                    len(final_response),
                    self._preview(final_response),
                )
                if self._memory_store:
                    self._memory_store.add_interaction(prompt, final_response)
                return final_response

            self._logger.info("LLM requested %s tool call(s)", len(response.function_calls))

            # Candidate content can be absent on some edge responses; keep safe fallback.
            function_call_content = (
                response.candidates[0].content
                if response.candidates and response.candidates[0].content is not None
                else types.Content(role="model", parts=[])
            )

            function_response_parts: list[types.Part] = []
            for index, call in enumerate(response.function_calls, start=1):
                name = self._get_call_name(call) or "unknown"
                args = self._get_call_args(call)
                self._logger.info(
                    "Executing tool call %s/%s: name=%s args=%s",
                    index,
                    len(response.function_calls),
                    name,
                    args,
                )

                # ToolRegistry always returns dict with either {"result": ...} or {"error": ...}.
                tool_response = self._tool_registry.execute(name, args)
                self._logger.info("Tool finished: name=%s keys=%s", name, list(tool_response.keys()))
                function_response_parts.append(
                    types.Part.from_function_response(name=name, response=tool_response)
                )

            # Append both: model function call request + tool responses.
            # Function responses must be attached as role="user" for this SDK/API flow.
            contents.append(function_call_content)
            contents.append(types.Content(role="user", parts=function_response_parts))
            self._logger.debug("Conversation content items now: %s", len(contents))

        # Safety fallback if model keeps looping with tool calls.
        final_response = "Stopped after too many tool-call turns."
        self._logger.warning(final_response)
        if self._memory_store:
            self._memory_store.add_interaction(prompt, final_response)
        return final_response

    @staticmethod
    def _get_call_name(call: Any) -> str | None:
        """Extract function name from SDK call object variants."""
        if hasattr(call, "name") and call.name:
            return call.name
        if hasattr(call, "function_call") and getattr(call.function_call, "name", None):
            return call.function_call.name
        return None

    @staticmethod
    def _get_call_args(call: Any) -> dict[str, Any]:
        """Extract function args from SDK call object variants."""
        if hasattr(call, "args") and call.args is not None:
            return call.args
        if hasattr(call, "function_call") and getattr(call.function_call, "args", None) is not None:
            return call.function_call.args
        return {}

    @staticmethod
    def _preview(text: str, max_len: int = 120) -> str:
        """Short preview helper for cleaner logs."""
        clean = " ".join(text.split())
        if len(clean) <= max_len:
            return clean
        return clean[: max_len - 3] + "..."
