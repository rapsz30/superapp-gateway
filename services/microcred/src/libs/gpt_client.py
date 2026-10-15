"""
GPT Client for essay scoring.

Provides async HTTP client for OpenAI API with retry logic
and exponential backoff.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx
import structlog
from src.core.config import get_settings

logger = structlog.get_logger()


class GPTClientError(Exception):
    """Base exception for GPT client errors."""


class GPTRateLimitError(GPTClientError):
    """Raised when rate limited by OpenAI."""


class GPTTimeoutError(GPTClientError):
    """Raised when request times out."""


class GPTAPIError(GPTClientError):
    """Raised for other API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class GPTResponse:
    """Parsed GPT response."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    finish_reason: str


class GPTClientProtocol(Protocol):
    """Protocol for GPT client (allows mocking)."""

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> GPTResponse:
        """Send chat completion request."""
        ...


class OpenAIClient:
    """Async OpenAI API client with retry logic."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model
        self.max_retries = max_retries if max_retries is not None else settings.gpt_max_retries
        self.timeout = (
            timeout_seconds if timeout_seconds is not None else settings.gpt_timeout_seconds
        )

        if not self.api_key:
            logger.warning("openai_api_key_missing", msg="OPENAI_API_KEY not configured")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> GPTResponse:
        """
        Send chat completion request with retry logic.

        Implements exponential backoff: 1s, 2s, 4s for retries.
        """
        if not self.api_key:
            raise GPTClientError("OPENAI_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            start_time = datetime.now(UTC)

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data, latency_ms)

                if response.status_code == 429:
                    # Rate limited - retry with backoff
                    error_message = self._extract_error_message(response)
                    error = GPTRateLimitError(
                        f"Rate limited (attempt {attempt + 1}): {error_message}"
                    )
                    last_error = error
                    await logger.awarning(
                        "gpt_rate_limited",
                        error=error_message,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                    )
                elif response.status_code >= 500:
                    # Server error - retry
                    error_message = self._extract_error_message(response)
                    error = GPTAPIError(
                        f"Server error {response.status_code}: {error_message}",
                        status_code=response.status_code,
                    )
                    last_error = error
                    await logger.awarning(
                        "gpt_server_error",
                        status_code=response.status_code,
                        error=error_message,
                        attempt=attempt + 1,
                    )
                else:
                    # Client error - don't retry
                    error_body = self._extract_error_message(response)
                    raise GPTAPIError(
                        f"API error {response.status_code}: {error_body}",
                        status_code=response.status_code,
                    )

            except httpx.TimeoutException:
                last_error = GPTTimeoutError(f"Request timed out (attempt {attempt + 1})")
                await logger.awarning(
                    "gpt_timeout",
                    attempt=attempt + 1,
                    timeout_seconds=self.timeout,
                )

            except httpx.RequestError as e:
                last_error = GPTClientError(f"Request failed: {e}")
                await logger.awarning(
                    "gpt_request_error",
                    error=str(e),
                    attempt=attempt + 1,
                )

            # Exponential backoff: 1s, 2s, 4s
            if attempt < self.max_retries - 1:
                backoff = 2**attempt
                await asyncio.sleep(backoff)

        # All retries exhausted
        raise last_error or GPTClientError("All retries exhausted")

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Extract a concise error message from API response body."""
        try:
            payload = response.json()
        except Exception:
            return response.text[:400]

        if isinstance(payload, dict):
            error_obj = payload.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()[:400]
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:400]

        return str(payload)[:400]

    def _parse_response(self, data: dict[str, Any], latency_ms: int) -> GPTResponse:
        """Parse OpenAI API response."""
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return GPTResponse(
            content=choice["message"]["content"],
            model=data["model"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason", "unknown"),
        )
