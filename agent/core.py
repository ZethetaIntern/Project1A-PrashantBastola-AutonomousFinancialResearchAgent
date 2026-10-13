"""Core loop for the autonomous financial research agent."""

import json
import logging
from typing import Any

from llm.client import LLMClient
from tools.tool_registry import ToolRegistry, build_default_registry
from agent.parser import ResponseParseError, parse_response
from agent.prompts import build_system_prompt

logger = logging.getLogger(__name__)


class AgentError(RuntimeError):
    """Raised when the agent cannot complete a research request."""


class FinancialResearchAgent:
    """Coordinate LLM responses, tool execution, and final answers."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        tool_registry: ToolRegistry | None = None,
        max_iterations: int = 8,
        max_tokens: int = 1200,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1.")
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1.")

        self.llm_client = llm_client or LLMClient()
        self.tool_registry = tool_registry or build_default_registry()
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens

    def run(self, query: str) -> dict[str, Any]:
        """Run a research query until a final answer or iteration limit."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Research query cannot be empty.")

        tools = self.tool_registry.list_tools()
        system_prompt = build_system_prompt(tools)

        messages: list[dict[str, str]] = [
            {"role": "user", "content": query.strip()}
        ]
        tool_history: list[dict[str, Any]] = []

        logger.info(
            "Agent started: max_iterations=%s query=%s",
            self.max_iterations,
            query.strip(),
        )

        for iteration in range(1, self.max_iterations + 1):
            prompt = (
                f"Research conversation so far:\n"
                f"{json.dumps(messages, ensure_ascii=False, indent=2)}\n\n"
                f"Tool execution history:\n"
                f"{json.dumps(tool_history, ensure_ascii=False, indent=2)}\n\n"
                "Decide whether to call an available tool or provide the "
                "final answer. Follow the required JSON response format."
            )

            logger.info(
                "Agent iteration %s/%s",
                iteration,
                self.max_iterations,
            )

            try:
                response = self.llm_client.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=self.max_tokens,
                )
                parsed = parse_response(response.text)
            except (ResponseParseError, ValueError, TypeError) as exc:
                logger.warning(
                    "Agent could not process LLM response at iteration %s: %s",
                    iteration,
                    exc,
                )
                raise AgentError(
                    f"Could not process the LLM response at iteration "
                    f"{iteration}: {exc}"
                ) from exc
            except Exception as exc:
                logger.exception("LLM request failed at iteration %s", iteration)
                raise AgentError(
                    f"LLM request failed at iteration {iteration}."
                ) from exc

            if parsed.response_type == "final":
                answer = parsed.content.strip()
                logger.info(
                    "Agent completed after %s iteration(s).",
                    iteration,
                )
                return {
                    "answer": answer,
                    "iterations": iteration,
                    "tool_calls": tool_history,
                    "usage": self.llm_client.get_usage(),
                    "status": "completed",
                }

            if parsed.response_type != "tool_call":
                raise AgentError(
                    f"Unsupported response type: {parsed.response_type}"
                )

            tool_name = parsed.tool_name
            arguments = parsed.arguments or {}

            logger.info(
                "Agent requested tool: name=%s arguments=%s",
                tool_name,
                arguments,
            )

            result = self.tool_registry.execute(tool_name, arguments)
            tool_history.append(
                {
                    "iteration": iteration,
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result,
                }
            )

            # Feed the tool result back into the next LLM request.
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "tool_call": {
                                "name": tool_name,
                                "arguments": arguments,
                            }
                        },
                        ensure_ascii=False,
                    ),
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Tool result:\n"
                        + json.dumps(result, ensure_ascii=False)
                        + "\nUse this result as evidence. If the tool failed, "
                        "acknowledge that limitation. Continue research or "
                        "provide your final answer."
                    ),
                }
            )

        logger.warning(
            "Agent reached maximum iterations (%s).",
            self.max_iterations,
        )
        return {
            "answer": (
                "Research stopped because the maximum number of agent "
                "iterations was reached. The available evidence may be "
                "incomplete."
            ),
            "iterations": self.max_iterations,
            "tool_calls": tool_history,
            "usage": self.llm_client.get_usage(),
            "status": "max_iterations_reached",
        }


def create_agent(
    max_iterations: int = 8,
    max_tokens: int = 1200,
) -> FinancialResearchAgent:
    """Construct an agent with the default LLM client and tools."""
    return FinancialResearchAgent(
        max_iterations=max_iterations,
        max_tokens=max_tokens,
    )
