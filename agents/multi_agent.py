from __future__ import annotations

"""Two-agent coordination flow.

Roles:
- planner: turns user request into a short plan.
- executor: follows plan and uses tools.

Mailbox captures every step so you can inspect agent-to-agent dialog.
"""

import logging
import uuid

from agents.agent import GeminiToolAgent
from stores.mailbox import MailboxStore
from tools.registry import ToolRegistry


class MultiAgentCoordinator:
    """Coordinator for planner -> executor -> planner cycle."""

    def __init__(
        self,
        model: str,
        planner_registry: ToolRegistry,
        executor_registry: ToolRegistry,
        mailbox: MailboxStore,
        max_turns: int = 5,
    ) -> None:
        self._logger = logging.getLogger("agent.coordinator")
        self._mailbox = mailbox

        # Planner should not use tools; it should produce a clear plan.
        self._planner = GeminiToolAgent(
            model=model,
            tool_registry=planner_registry,
            system_prompt=(
                "You are a planner. Produce a short, numbered plan for the executor. "
                "Do not call tools."
            ),
            max_turns=max_turns,
        )

        # Executor can use tools and convert plan into concrete results.
        self._executor = GeminiToolAgent(
            model=model,
            tool_registry=executor_registry,
            system_prompt=(
                "You are an executor. Follow the plan, call tools when needed, and return results."
            ),
            max_turns=max_turns,
        )

    def run(self, prompt: str) -> str:
        """Run one multi-agent session and return final user-facing response."""
        thread_id = str(uuid.uuid4())
        self._logger.info("Multi-agent run started: thread=%s prompt=%s", thread_id, self._preview(prompt))

        # Step 1: user request enters mailbox for traceability.
        self._mailbox.send("user", "planner", {"prompt": prompt}, thread_id)

        # Step 2: planner creates plan.
        plan = self._planner.run(
            "User request:\n"
            f"{prompt}\n\n"
            "Return a short numbered plan for the executor."
        )
        self._logger.info("Planner produced plan: %s chars", len(plan))
        self._mailbox.send("planner", "executor", {"plan": plan, "prompt": prompt}, thread_id)

        # Step 3: executor performs plan and can call tools.
        result = self._executor.run(
            "User request:\n"
            f"{prompt}\n\n"
            "Plan:\n"
            f"{plan}\n\n"
            "Execute the plan and provide results."
        )
        self._logger.info("Executor produced result: %s chars", len(result))
        self._mailbox.send("executor", "planner", {"result": result}, thread_id)

        # Step 4: planner converts executor result into final answer for user.
        final_response = self._planner.run(
            "User request:\n"
            f"{prompt}\n\n"
            "Executor result:\n"
            f"{result}\n\n"
            "Write the final response for the user."
        )
        self._mailbox.send("planner", "user", {"final": final_response}, thread_id)

        self._logger.info(
            "Multi-agent run completed: thread=%s final_chars=%s preview=%s",
            thread_id,
            len(final_response),
            self._preview(final_response),
        )
        return final_response

    @staticmethod
    def _preview(text: str, max_len: int = 120) -> str:
        clean = " ".join(text.split())
        if len(clean) <= max_len:
            return clean
        return clean[: max_len - 3] + "..."
