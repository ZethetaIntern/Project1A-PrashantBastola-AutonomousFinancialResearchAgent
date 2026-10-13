
"""Tests for the provider-independent LLM client."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from llm.client import LLMClient


def fake_response(
    text="Market outlook is positive.",
    input_tokens=12,
    output_tokens=8,
):
    """Build a mock LiteLLM response without making an API call."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text)
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        ),
        _hidden_params={},
    )


def test_client_initializes_with_zero_usage():
    """A new client should start with zero recorded usage."""
    client = LLMClient()

    usage = client.get_usage()

    assert usage["request_count"] == 0
    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0
    assert usage["total_tokens"] == 0
    assert usage["estimated_cost_usd"] == 0.0


def test_empty_prompt_is_rejected():
    """An empty prompt should fail before calling the provider."""
    client = LLMClient()

    with pytest.raises(ValueError, match="prompt cannot be empty"):
        client.complete("   ")


def test_invalid_max_tokens_is_rejected():
    """The maximum token limit must be positive."""
    client = LLMClient()

    with pytest.raises(ValueError, match="max_tokens must be at least 1"):
        client.complete("Analyze this company", max_tokens=0)


def test_successful_response_records_token_usage():
    """A successful mocked response should update usage counters."""
    client = LLMClient()

    with (
        patch(
            "llm.client.completion",
            return_value=fake_response(),
        ) as mocked,
        patch("llm.client.settings.GROQ_API_KEY", "test-key"),
    ):
        response = client.complete(
            "Analyze this company",
            system_prompt="You are a financial research assistant.",
        )

    assert response.text == "Market outlook is positive."
    assert response.input_tokens == 12
    assert response.output_tokens == 8
    assert response.total_tokens == 20
    assert response.provider == client.provider
    assert response.model == client.model

    usage = client.get_usage()
    assert usage["request_count"] == 1
    assert usage["input_tokens"] == 12
    assert usage["output_tokens"] == 8
    assert usage["total_tokens"] == 20

    mocked.assert_called_once()


def test_multiple_successful_calls_accumulate_usage():
    """Token usage should accumulate across successful calls."""
    client = LLMClient()

    with (
        patch(
            "llm.client.completion",
            side_effect=[
                fake_response(input_tokens=10, output_tokens=5),
                fake_response(input_tokens=20, output_tokens=7),
            ],
        ) as mocked,
        patch("llm.client.settings.GROQ_API_KEY", "test-key"),
    ):
        client.complete("First question")
        client.complete("Second question")

    usage = client.get_usage()

    assert usage["request_count"] == 2
    assert usage["input_tokens"] == 30
    assert usage["output_tokens"] == 12
    assert usage["total_tokens"] == 42
    assert mocked.call_count == 2


def test_missing_provider_key_is_rejected_without_api_call():
    """A missing API key should stop the request before LiteLLM."""
    client = LLMClient()
    client.provider = "groq"

    with (
        patch("llm.client.completion") as mocked,
        patch("llm.client.settings.GROQ_API_KEY", ""),
        pytest.raises(ValueError, match="GROQ_API_KEY is missing"),
    ):
        client.complete("Analyze this company")

    mocked.assert_not_called()


def test_temporary_server_error_is_retried():
    """A temporary server error should trigger a retry."""
    client = LLMClient()

    temporary_error = Exception("temporary server failure")
    temporary_error.status_code = 503

    with (
        patch(
            "llm.client.completion",
            side_effect=[
                temporary_error,
                fake_response(),
            ],
        ) as mocked,
        patch("llm.client.settings.GROQ_API_KEY", "test-key"),
        patch("llm.client.wait_exponential") as wait_mock,
    ):
        # Avoid real waiting during this unit test.
        wait_mock.return_value = lambda retry_state: 0

        response = client.complete("Analyze this company")

    assert response.text == "Market outlook is positive."
    assert mocked.call_count == 2

    usage = client.get_usage()
    assert usage["request_count"] == 1
    assert usage["input_tokens"] == 12
    assert usage["output_tokens"] == 8
