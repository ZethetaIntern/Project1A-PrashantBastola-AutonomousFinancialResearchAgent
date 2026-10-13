
import pytest

from tools.tool_registry import (
    ToolNotFoundError,
    ToolValidationError,
    build_default_registry,
)


@pytest.fixture
def registry():
    return build_default_registry()

def test_registry_contains_expected_tools(registry):
    names = {
        item["function"]["name"]
        for item in registry.list_tools()
    }

    expected = {
        "calculator",
        "company_profile",
        "fact_checker",
        "sec_edgar",
        "financial_api",
        "web_search",
    }

    assert expected.issubset(names)


def test_calculator_executes_successfully(registry):
    result = registry.execute(
        "calculator",
        {"operation": "divide", "a": 100, "b": 4},
    )

    assert result["success"] is True
    assert result["data"]["result"] == 25.0


def test_calculator_rejects_string_number(registry):
    with pytest.raises(ToolValidationError):
        registry.execute(
            "calculator",
            {"operation": "divide", "a": "100", "b": 4},
        )


def test_company_profile_returns_mock_data(registry):
    result = registry.execute(
        "company_profile",
        {"ticker": "MSFT"},
    )

    assert result["success"] is True
    assert result["data"]["ticker"] == "MSFT"
    assert result["data"]["data_source"] == "mock"


def test_fact_checker_does_not_claim_independent_verification(registry):
    result = registry.execute(
        "fact_checker",
        {
            "claim": "Revenue increased 10%",
            "sources": ["Example source"],
        },
    )

    assert result["success"] is True
    assert result["data"]["status"] == (
        "evidence_provided_not_independently_verified"
    )


def test_unknown_tool_is_rejected(registry):
    with pytest.raises(ToolNotFoundError):
        registry.execute("unknown_tool", {})



def test_registry_rejects_missing_required_arguments(registry):
    with pytest.raises(ToolValidationError):
        registry.execute("calculator", {"operation": "add", "a": 5})


def test_registry_rejects_unexpected_arguments(registry):
    with pytest.raises(ToolValidationError):
        registry.execute(
            "calculator",
            {"operation": "add", "a": 5, "b": 2, "extra": 1},
        )


def test_registry_rejects_invalid_enum_value(registry):
    with pytest.raises(ToolValidationError):
        registry.execute(
            "calculator",
            {"operation": "power", "a": 2, "b": 3},
        )


def test_tool_errors_return_structured_failure(registry):
    result = registry.execute(
        "calculator",
        {"operation": "divide", "a": 10, "b": 0},
    )

    assert result["success"] is False
    assert result["data"] is None
    assert result["error"] is not None
