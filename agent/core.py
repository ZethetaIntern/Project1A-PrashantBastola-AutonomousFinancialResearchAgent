
"""Core loop for the autonomous financial research agent."""

import logging
from typing import Any

from agent.parser import ResponseParseError, parse_response
from agent.prompts import build_system_prompt
from llm.client import LLMClient
from tools.tool_registry import ToolRegistry, build_default_registry

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_TOOLS = {
    "company_profile",
    "financial_api",
    "web_search",
}


class AgentError(Exception):
    """Raised when the agent cannot process an LLM response."""


class FinancialResearchAgent:
    """Gather research evidence and synthesize a final answer."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        max_iterations: int = 5,
        max_tokens: int = 800,
        allowed_tools: set[str] | None = None,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")

        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.allowed_tools = (
            set(allowed_tools)
            if allowed_tools is not None
            else set(DEFAULT_ALLOWED_TOOLS)
        )

    def run(self, query: str) -> dict[str, Any]:
        """Run the research workflow and return its answer and evidence."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query cannot be empty")

        tool_history: list[dict[str, Any]] = []
        executed_calls: set[tuple[str, str]] = set()
        research_context = ""
        final_answer = ""
        status = "max_iterations_reached"
        iterations_used = 0

        available_tools = [
            tool
            for tool in self.tool_registry.list_tools()
            if tool.get("function", {}).get("name")
            in self.allowed_tools
        ]

        system_prompt = build_system_prompt(available_tools)

        def make_result(
            result_status: str,
            answer: str,
            iterations: int,
            error: str | None = None,
        ) -> dict[str, Any]:
            """Return a consistent result with tool history and usage."""

            result: dict[str, Any] = {
                "status": result_status,
                "answer": answer,
                "iterations": iterations,
                "tool_calls": tool_history,
            }

            try:
                usage = self.llm_client.get_usage()
                if usage is not None:
                    result["usage"] = usage
            except Exception:
                logger.exception("Unable to retrieve LLM usage")

            if error:
                result["error"] = error

            return result

        for iteration in range(1, self.max_iterations + 1):
            iterations_used = iteration
            synthesis_only = iteration == self.max_iterations

            if synthesis_only:
                instruction = (
                    "FINAL SYNTHESIS: Do not call any tools. Answer the user's "
                    "original request using the evidence collected so far. "
                    "Clearly identify missing information and limitations. "
                    "Do not invent facts, figures, estimates, citations, "
                    "executives, or events. Return a final answer using "
                    'JSON: {"type":"final","answer":"your complete answer"} '
                    'or {"action":"final","answer":"your complete answer"}.'
                )
            else:
                instruction = (
                    "Continue researching the user's request using available "
                    "tools when useful. Do not repeat a tool call with the "
                    "same arguments. If enough evidence is available, return "
                    "a final answer. For a tool call, return JSON such as "
                    '{"action":"execute","name":"company_profile",'
                    '"arguments":{"ticker":"MSFT"}} or the legacy format '
                    '{"tool_call":{"name":"company_profile",'
                    '"arguments":{"ticker":"MSFT"}}}. For a final answer, '
                    'return {"type":"final","answer":"your answer"}.'
                )



            prompt = (
                f"User request:\n{query}\n\n"
                f"Research evidence collected so far:\n"
                f"{research_context or 'No evidence collected yet.'}\n\n"
                f"{instruction}"
            )



            try:
                response = self.llm_client.complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=self.max_tokens,
                )
                parsed = parse_response(response.text)

            except (ResponseParseError, ValueError, TypeError) as exc:
                raise AgentError(
                    f"Could not process the LLM response at iteration "
                    f"{iteration}: {exc}"
                ) from exc

            except Exception as exc:
                logger.exception(
                    "LLM request failed at iteration %s",
                    iteration,
                )
                return make_result(
                    result_status="failed",
                    answer=(
                        "The agent could not complete the research report. "
                        "Collected evidence is preserved in tool_calls."
                    ),
                    iterations=iteration,
                    error=f"{type(exc).__name__}: {exc}",
                )

            # The parser returns a ParsedResponse dataclass, not a dictionary.
            if parsed.response_type == "final":
                final_answer = parsed.content.strip()

                if not final_answer:
                    return make_result(
                        result_status="failed",
                        answer="The model returned an empty final answer.",
                        iterations=iteration,
                        error="Empty final answer",
                    )

                status = "completed"
                break

            if parsed.response_type != "tool_call":
                raise AgentError(
                    f"Could not process the LLM response at iteration "
                    f"{iteration}: unexpected response type "
                    f"{parsed.response_type!r}"
                )

            tool_name = parsed.tool_name
            arguments = parsed.arguments or {}

            if not tool_name:
                raise AgentError(
                    f"Could not process the LLM response at iteration "
                    f"{iteration}: missing tool name"
                )

            # Never execute tools on the reserved synthesis iteration.
            if synthesis_only:
                status = "max_iterations_reached"
                final_answer = (
                    "Research reached its iteration limit without a final "
                    "answer. Review the collected evidence in tool_calls."
                )
                break

            if tool_name not in self.allowed_tools:
                tool_history.append(
                    {
                        "iteration": iteration,
                        "tool": tool_name,
                        "arguments": arguments,
                        "status": "rejected",
                        "error": "Tool is not allowed for this research run.",
                    }
                )
                continue

            # A stable JSON representation supports nested argument values.
            import json

            call_key = (
                tool_name,
                json.dumps(arguments, sort_keys=True, default=str),
            )

            if call_key in executed_calls:
                tool_history.append(
                    {
                        "iteration": iteration,
                        "tool": tool_name,
                        "arguments": arguments,
                        "status": "skipped_duplicate",
                    }
                )
                continue

            executed_calls.add(call_key)

            try:
                tool_result = self.tool_registry.execute(
                    tool_name,
                    arguments,
                )

                succeeded = (
                    isinstance(tool_result, dict)
                    and tool_result.get("success") is not False
                    and not tool_result.get("error")
                )

                record = {
                    "iteration": iteration,
                    "tool": tool_name,
                    "arguments": arguments,
                    "status": "success" if succeeded else "failed",
                    "result": tool_result,
                }

                if not succeeded:
                    record["error"] = (
                        tool_result.get("error", "Tool execution failed.")
                        if isinstance(tool_result, dict)
                        else "Tool returned an invalid result."
                    )

                tool_history.append(record)

                evidence = (
                    f"\n\nTool: {tool_name}\n"
                    f"Arguments: {json.dumps(arguments, default=str)}\n"
                    f"Result: {json.dumps(tool_result, default=str)}"
                )
                research_context = (research_context + evidence)[-6000:]

            except Exception as exc:
                logger.exception("Tool execution failed: %s", tool_name)

                tool_history.append(
                    {
                        "iteration": iteration,
                        "tool": tool_name,
                        "arguments": arguments,
                        "status": "failed",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

                # Continue to the next LLM iteration so the model can
                # respond to the tool failure or try another tool.

        if not final_answer:
            final_answer = (
                "Research stopped at the iteration limit. "
                "The collected evidence may be incomplete."
            )

        return make_result(
            result_status=status,
            answer=final_answer,
            iterations=iterations_used,
        )


def create_agent(
    max_iterations: int = 5,
    max_tokens: int = 800,
    allowed_tools: set[str] | None = None,
) -> FinancialResearchAgent:
    """Create an agent using the default LLM client and tool registry."""

    return FinancialResearchAgent(
        llm_client=LLMClient(),
        tool_registry=build_default_registry(),
        max_iterations=max_iterations,
        max_tokens=max_tokens,
        allowed_tools=allowed_tools,
    )
