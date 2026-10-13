
"""Provider-independent LLM client with retries and usage tracking."""

import logging
from dataclasses import dataclass
from typing import Optional

import litellm
from litellm import completion
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from config.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


# Prevent LiteLLM from retrying independently of Tenacity.
litellm.num_retries = 0


@dataclass
class LLMResponse:
    """A consistent response format across supported LLM providers."""

    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Optional[float] = None

    @property
    def total_tokens(self) -> int:
        """Return the combined input and output token count."""
        return self.input_tokens + self.output_tokens


def _is_retryable(exc: BaseException) -> bool:
    """Retry transient network, rate-limit, and server errors."""
    if isinstance(exc, (ValueError, TypeError)):
        return False

    status_code = getattr(exc, "status_code", None)

    # Retry rate limits, server errors, and temporary gateway errors.
    if status_code == 429 or (
        isinstance(status_code, int) and status_code >= 500
    ):
        return True

    # Retry connection failures and timeouts, not ordinary bad requests.
    name = type(exc).__name__.lower()
    return any(
        marker in name
        for marker in ("timeout", "connection", "ratelimit", "internalserver")
    )


class LLMClient:
    """Call multiple LLM providers through LiteLLM."""

    def __init__(self) -> None:
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_estimated_cost_usd = 0.0
        self.request_count = 0

    def _run_with_retry(self, operation):
        """Retry transient failures with exponential backoff."""
        retryer = Retrying(
            stop=stop_after_attempt(settings.MAX_RETRIES + 1),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception(_is_retryable),
            before_sleep=lambda state: logger.warning(
                "LLM request failed; retrying attempt %s of %s: %s",
                state.attempt_number,
                settings.MAX_RETRIES + 1,
                state.outcome.exception() if state.outcome else "unknown error",
            ),
            reraise=True,
        )
        return retryer(operation)

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate a response and record provider-reported usage."""
        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "timeout": settings.TOOL_TIMEOUT_SECONDS,
        }

        # LiteLLM uses these environment variables for authentication.
        provider_env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }

        if self.provider != "ollama":
            env_name = provider_env_vars[self.provider]
            api_key = getattr(settings, env_name)
            if not api_key:
                raise ValueError(
                    f"{env_name} is missing. Configure it in your local .env."
                )
            kwargs["api_key"] = api_key
        else:
            kwargs["api_base"] = settings.OLLAMA_BASE_URL.rstrip("/") + "/v1"

        logger.info(
            "Starting LLM request: provider=%s model=%s",
            self.provider,
            self.model,
        )

        response = self._run_with_retry(lambda: completion(**kwargs))

        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)

        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0

        # Some LiteLLM responses provide cost metadata; not all do.
        cost = None
        hidden_params = getattr(response, "_hidden_params", {}) or {}
        raw_cost = hidden_params.get("response_cost")
        if raw_cost is not None:
            cost = float(raw_cost)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.request_count += 1

        if cost is not None:
            self.total_estimated_cost_usd += cost

        logger.info(
            "LLM request succeeded: provider=%s model=%s input_tokens=%s "
            "output_tokens=%s cost_usd=%s",
            self.provider,
            self.model,
            input_tokens,
            output_tokens,
            cost,
        )

        return LLMResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
        )

    def get_usage(self) -> dict:
        """Return cumulative usage for this client instance."""
        return {
            "request_count": self.request_count,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": (
                self.total_input_tokens + self.total_output_tokens
            ),
            "estimated_cost_usd": round(
                self.total_estimated_cost_usd, 8
            ),
        }
