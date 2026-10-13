"""Tests for the financial research agent core loop."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.core import AgentError, FinancialResearchAgent
from tools.tool_registry import ToolRegistry



@pytest.fixture
def mock_registry():
    def mock_company_profile(ticker):
        profiles = {
            "MSFT": {
                "company_name": "Microsoft Corporation",
                "ticker": "MSFT",
                "sector": "Technology",
                "industry": "Software",
                "data_source": "mock",
            }
        }

        normalized_ticker = ticker.strip().upper()

        if normalized_ticker not in profiles:
            raise ValueError(
                f"No mock profile available for ticker: {normalized_ticker}"
            )

        return dict(profiles[normalized_ticker])

    registry = ToolRegistry()
    registry.register(
        name="company_profile",
        description="Retrieve a mock company profile by ticker.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
            },
            "required": ["ticker"],
            "additionalProperties": False,
        },
        function=mock_company_profile,
    )
    return registry



def mock_response(text):
    return SimpleNamespace(text=text)


def test_microsoft_profile_workflow(mock_registry):
    llm = Mock()
    llm.complete.side_effect = [
        mock_response(
            '{"tool_call": {"name": "company_profile", '
            '"arguments": {"ticker": "MSFT"}}}'
        ),
        mock_response(
            '{"type": "final", "answer": '
            '"Microsoft Corporation (MSFT) operates in the technology '
            'sector and software industry. The profile uses mock data."}'
        ),
    ]
    llm.get_usage.return_value = {"total_tokens": 100}

    agent = FinancialResearchAgent(
        llm_client=llm,
        tool_registry=mock_registry,
        max_iterations=4,
    )

    result = agent.run("Research Microsoft's company profile.")

    assert result["status"] == "completed"
    assert "Microsoft Corporation" in result["answer"]
    assert result["iterations"] == 2
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["tool"] == "company_profile"
    assert result["tool_calls"][0]["result"]["success"] is True
    assert result["tool_calls"][0]["result"]["data"]["ticker"] == "MSFT"


def test_agent_rejects_empty_query(mock_registry):
    agent = FinancialResearchAgent(
        llm_client=Mock(),
        tool_registry=mock_registry,
    )

    with pytest.raises(ValueError, match="cannot be empty"):
        agent.run("   ")


def test_agent_stops_at_iteration_limit(mock_registry):
    llm = Mock()
    llm.complete.return_value = mock_response(
        '{"tool_call": {"name": "company_profile", '
        '"arguments": {"ticker": "MSFT"}}}'
    )
    llm.get_usage.return_value = {"total_tokens": 100}

    agent = FinancialResearchAgent(
        llm_client=llm,
        tool_registry=mock_registry,
        max_iterations=2,
    )

    result = agent.run("Research Microsoft.")

    assert result["status"] == "max_iterations_reached"
    assert result["iterations"] == 2
    assert len(result["tool_calls"]) == 2
    assert llm.complete.call_count == 2


def test_agent_wraps_invalid_json_response(mock_registry):
    llm = Mock()
    llm.complete.return_value = mock_response(
        '{"tool_call": '
    )

    agent = FinancialResearchAgent(
        llm_client=llm,
        tool_registry=mock_registry,
    )

    with pytest.raises(AgentError, match="Could not process"):
        agent.run("Research Microsoft.")
def test_agent_continues_after_tool_failure(mock_registry):
    llm = Mock()
    llm.complete.side_effect = [
        mock_response(
            '{"tool_call": {"name": "company_profile", '
            '"arguments": {"ticker": "UNKNOWN"}}}'
        ),
        mock_response(
            '{"type": "final", "answer": '
            '"I could not retrieve the company profile because the tool failed."}'
        ),
    ]
    llm.get_usage.return_value = {"total_tokens": 100}

    agent = FinancialResearchAgent(
        llm_client=llm,
        tool_registry=mock_registry,
        max_iterations=4,
    )

    result = agent.run("Research the company with ticker UNKNOWN.")

    assert result["status"] == "completed"
    assert "tool failed" in result["answer"].lower()
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["result"]["success"] is False
