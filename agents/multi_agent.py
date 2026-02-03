from __future__ import annotations

import logging
import uuid

from agents.agent import GeminiToolAgent
from stores.mailbox import MailboxStore
from tools.registry import ToolRegistry


class MultiAgentCoordinator:
    """Координатор пары планировщик -> исполнитель через mailbox."""

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
        self._planner = GeminiToolAgent(
            model=model,
            tool_registry=planner_registry,
            system_prompt=(
                "You are a planner. Produce a short, numbered plan for the executor. "
                "Do not call tools."
            ),
            max_turns=max_turns,
        )
        self._executor = GeminiToolAgent(
            model=model,
            tool_registry=executor_registry,
            system_prompt=(
                "You are an executor. Follow the plan, call tools when needed, and return results."
            ),
            max_turns=max_turns,
        )

    def run(self, prompt: str) -> str:
        thread_id = str(uuid.uuid4())
        self._mailbox.send("user", "planner", {"prompt": prompt}, thread_id)
        self._logger.info("Planner requested: thread=%s", thread_id)

        plan = self._planner.run(
            "User request:\n"
            f"{prompt}\n\n"
            "Return a short numbered plan for the executor."
        )
        self._mailbox.send("planner", "executor", {"plan": plan, "prompt": prompt}, thread_id)

        result = self._executor.run(
            "User request:\n"
            f"{prompt}\n\n"
            "Plan:\n"
            f"{plan}\n\n"
            "Execute the plan and provide results."
        )
        self._mailbox.send("executor", "planner", {"result": result}, thread_id)

        final_response = self._planner.run(
            "User request:\n"
            f"{prompt}\n\n"
            "Executor result:\n"
            f"{result}\n\n"
            "Write the final response for the user."
        )
        self._mailbox.send("planner", "user", {"final": final_response}, thread_id)
        return final_response
