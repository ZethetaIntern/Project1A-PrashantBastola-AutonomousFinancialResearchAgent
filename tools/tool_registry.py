
"""Registry for the financial research agent's tools."""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from config.logging_config import setup_logging
from tools.calculator import calculate
from tools.company_profile import get_company_profile
from tools.earnings import get_earnings
from tools.fact_checker import check_claim
from tools.financial_api import get_financial_data
from tools.news_sentiment import analyze_news_sentiment
from tools.peer_comparison import compare_peers
from tools.report_gen import generate_report
from tools.sec_edgar import search_sec_filings
from tools.web_search import search_web


setup_logging()
logger = logging.getLogger(__name__)

SCHEMA_DIR = Path(__file__).parent / "schemas"


class ToolValidationError(ValueError):
    """Raised when a tool call has invalid input."""


class ToolNotFoundError(LookupError):
    """Raised when a requested tool is not registered."""


@dataclass
class Tool:
    """Represent a registered research tool."""

    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., dict[str, Any]]


class ToolRegistry:
    """Register, validate, and execute research tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        function: Callable[..., dict[str, Any]],
    ) -> None:
        """Register a tool with its description, schema, and function."""
        if not name or not name.replace("_", "").isalnum():
            raise ValueError(
                "Tool name must contain only letters, numbers, and underscores."
            )

        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")

        if parameters.get("type") != "object":
            raise ValueError("Tool parameters must use a JSON Schema object.")

        self._tools[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=function,
        )

        logger.info("Tool registered: %s", name)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return tool metadata in function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def _validate(
        self,
        schema: dict[str, Any],
        arguments: dict[str, Any],
    ) -> None:
        """Validate tool arguments against the supported JSON Schema rules."""
        if not isinstance(arguments, dict):
            raise ToolValidationError("Tool arguments must be a JSON object.")

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        missing = [key for key in required if key not in arguments]
        if missing:
            raise ToolValidationError(
                f"Missing required argument(s): {', '.join(missing)}"
            )

        additional = schema.get("additionalProperties", True)
        if additional is False:
            unknown = [key for key in arguments if key not in properties]
            if unknown:
                raise ToolValidationError(
                    f"Unexpected argument(s): {', '.join(unknown)}"
                )

        valid_types = {
            "string": lambda value: isinstance(value, str),
            "integer": lambda value: (
                isinstance(value, int) and not isinstance(value, bool)
            ),
            "number": lambda value: (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            ),
            "boolean": lambda value: isinstance(value, bool),
            "object": lambda value: isinstance(value, dict),
            "array": lambda value: isinstance(value, list),
        }

        for key, value in arguments.items():
            if key not in properties:
                continue

            rule = properties[key]
            expected = rule.get("type")

            if expected in valid_types and not valid_types[expected](value):
                raise ToolValidationError(
                    f"'{key}' must be of type {expected}."
                )

            if "enum" in rule and value not in rule["enum"]:
                raise ToolValidationError(
                    f"'{key}' must be one of {rule['enum']}."
                )

            if isinstance(value, str):
                if len(value) < rule.get("minLength", 0):
                    raise ToolValidationError(f"'{key}' is too short.")

                if len(value) > rule.get("maxLength", float("inf")):
                    raise ToolValidationError(f"'{key}' is too long.")

            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if value < rule.get("minimum", float("-inf")):
                    raise ToolValidationError(
                        f"'{key}' is below the minimum."
                    )

                if value > rule.get("maximum", float("inf")):
                    raise ToolValidationError(
                        f"'{key}' exceeds the maximum."
                    )

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate, execute, and log a research tool call."""
        if name not in self._tools:
            logger.warning("Unknown tool requested: %s", name)
            raise ToolNotFoundError(f"Unknown tool: {name}")

        tool = self._tools[name]

        try:
            self._validate(tool.parameters, arguments)
        except ToolValidationError:
            logger.warning("Tool argument validation failed: %s", name)
            raise

        started = time.perf_counter()
        logger.info("Tool execution started: %s", name)

        try:
            result = tool.function(**arguments)

            if not isinstance(result, dict):
                raise TypeError("Tool must return a dictionary.")

            elapsed = time.perf_counter() - started
            logger.info(
                "Tool execution succeeded: %s (%.3f seconds)",
                name,
                elapsed,
            )

            return {
                "tool": name,
                "success": True,
                "data": result,
                "error": None,
            }

        except Exception as exc:
            elapsed = time.perf_counter() - started

            logger.exception(
                "Tool execution failed: %s (%.3f seconds)",
                name,
                elapsed,
            )

            return {
                "tool": name,
                "success": False,
                "data": None,
                "error": str(exc),
            }


def load_schema(filename: str) -> dict:
    """Load a JSON schema from the schemas directory."""
    with (SCHEMA_DIR / filename).open(encoding="utf-8") as file:
        return json.load(file)


def build_default_registry() -> ToolRegistry:
    """Create a registry containing all available research tools."""
    registry = ToolRegistry()

    registry.register(
        name="calculator",
        description="Perform basic arithmetic for financial research.",
        parameters=load_schema("calculator.json"),
        function=calculate,
    )

    registry.register(
        name="company_profile",
        description="Retrieve a mock company profile by ticker.",
        parameters=load_schema("company_profile.json"),
        function=get_company_profile,
    )

    registry.register(
        name="fact_checker",
        description="Assess whether evidence was supplied for a claim.",
        parameters=load_schema("fact_checker.json"),
        function=check_claim,
    )

    registry.register(
        name="sec_edgar",
        description=(
            "Search SEC filing metadata by ticker and filing type. "
            "Current implementation returns mock data only."
        ),
        parameters=load_schema("sec_edgar.json"),
        function=search_sec_filings,
    )

    registry.register(
        name="financial_api",
        description=(
            "Retrieve financial metrics for a company ticker. "
            "Current implementation returns mock data only."
        ),
        parameters=load_schema("financial_api.json"),
        function=get_financial_data,
    )

    registry.register(
        name="web_search",
        description=(
            "Search the web for financial research information. "
            "Currently uses a mock implementation."
        ),
        parameters=load_schema("web_search.json"),
        function=search_web,
    )

    registry.register(
        name="news_sentiment",
        description=(
            "Assess news sentiment for a company using supplied headlines. "
            "Currently does not run a sentiment model."
        ),
        parameters=load_schema("news_sentiment.json"),
        function=analyze_news_sentiment,
    )

    registry.register(
        name="earnings",
        description=(
            "Retrieve company earnings information and transcript metadata. "
            "Currently returns mock data only."
        ),
        parameters=load_schema("earnings.json"),
        function=get_earnings,
    )

    registry.register(
        name="peer_comparison",
        description=(
            "Prepare a comparison between a company and its peers. "
            "Currently returns mock data without financial metrics."
        ),
        parameters=load_schema("peer_comparison.json"),
        function=compare_peers,
    )

    registry.register(
        name="report_generator",
        description=(
            "Generate a structured financial research report from supplied "
            "findings. Does not independently verify claims or citations."
        ),
        parameters=load_schema("report_generator.json"),
        function=generate_report,
    )

    return registry
