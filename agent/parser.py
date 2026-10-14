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

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) < 3 or not lines[-1].strip().startswith("```"):
            raise ResponseParseError("Markdown code fence is not properly closed.")
        cleaned = "\n".join(lines[1:-1]).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        if cleaned.startswith(("{", "[")):
            raise ResponseParseError("LLM returned malformed JSON.") from exc
        return ParsedResponse(response_type="final", content=cleaned)

    if not isinstance(payload, dict):
        raise ResponseParseError("JSON response must be an object.")

    # Preferred format: {"action": "execute", "name": ..., "arguments": ...}
    # Legacy format remains supported: {"tool_call": {...}}
    if payload.get("action") == "execute":
        name = payload.get("name")
        arguments = payload.get("arguments", {})
    elif "tool_call" in payload:
        call = payload["tool_call"]
        if not isinstance(call, dict):
            raise ResponseParseError("'tool_call' must be an object.")
        name = call.get("name")
        arguments = call.get("arguments", {})
    else:
        name = None
        arguments = {}

    if payload.get("action") == "final" or payload.get("type") == "final":
        answer = payload.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise ResponseParseError("Final response requires a non-empty answer.")
        return ParsedResponse(response_type="final", content=answer.strip())

    if name is not None:
        if not isinstance(name, str) or not name.strip():
            raise ResponseParseError("Tool call requires a non-empty name.")
        if not isinstance(arguments, dict):
            raise ResponseParseError("Tool arguments must be a JSON object.")
        return ParsedResponse(
            response_type="tool_call",
            tool_name=name.strip(),
            arguments=arguments,
        )

    raise ResponseParseError(
        "JSON response must contain an execute action, a tool_call, or a final answer."
    )
