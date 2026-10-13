
"""Parse LLM responses into tool calls or final answers."""

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class ResponseParseError(ValueError):
    """Raised when an LLM response cannot be parsed safely."""


@dataclass
class ParsedResponse:
    """Represent a parsed agent response."""

    response_type: str
    content: str = ""
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None


def parse_response(text: str) -> ParsedResponse:
    """Parse a JSON tool call, JSON final answer, or plain-text answer."""

    if not isinstance(text, str) or not text.strip():
        raise ResponseParseError("LLM response cannot be empty.")

    cleaned = text.strip()

    # Support JSON enclosed in Markdown code fences.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if len(lines) < 3 or not lines[-1].strip().startswith("```"):
            raise ResponseParseError(
                "Markdown code fence is not properly closed."
            )

        # Remove the opening fence and optional language identifier.
        cleaned = "\n".join(lines[1:-1]).strip()

        if not cleaned:
            raise ResponseParseError(
                "Response inside the Markdown code fence is empty."
            )

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # JSON-like output must not silently become a final answer.
        if cleaned.startswith(("{", "[")):
            logger.warning("LLM returned malformed JSON.")
            raise ResponseParseError(
                "LLM returned malformed JSON."
            ) from exc

        # Permit ordinary prose as a final answer for compatibility.
        logger.debug("LLM response interpreted as a plain-text answer.")

        return ParsedResponse(
            response_type="final",
            content=cleaned,
        )

    if not isinstance(payload, dict):
        raise ResponseParseError("JSON response must be an object.")

    # Parse a tool call.
    if "tool_call" in payload:
        call = payload["tool_call"]

        if not isinstance(call, dict):
            raise ResponseParseError("'tool_call' must be an object.")

        name = call.get("name")
        arguments = call.get("arguments", {})

        if not isinstance(name, str) or not name.strip():
            raise ResponseParseError(
                "Tool call requires a non-empty name."
            )

        if not isinstance(arguments, dict):
            raise ResponseParseError(
                "Tool arguments must be a JSON object."
            )

        return ParsedResponse(
            response_type="tool_call",
            tool_name=name.strip(),
            arguments=arguments,
        )

    # Parse a structured final answer.
    if payload.get("type") == "final":
        answer = payload.get("answer")

        if not isinstance(answer, str) or not answer.strip():
            raise ResponseParseError(
                "Final response requires a non-empty answer."
            )

        return ParsedResponse(
            response_type="final",
            content=answer.strip(),
        )

    raise ResponseParseError(
        "JSON response must contain 'tool_call' or type='final'."
    )
