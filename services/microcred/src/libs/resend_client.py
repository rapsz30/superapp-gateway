"""
Resend API client for transactional emails.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog
from src.core.config import get_settings

logger = structlog.get_logger(__name__)


class ResendClientError(Exception):
    """Base exception for Resend client errors."""


class ResendAPIError(ResendClientError):
    """Raised for non-success responses from Resend."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class ResendEmailResponse:
    """Minimal Resend email response."""

    id: str


class ResendClient:
    """Async Resend API client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.resend_api_key
        self.base_url = base_url or settings.resend_base_url
        self.timeout = (
            timeout_seconds if timeout_seconds is not None else settings.resend_timeout_seconds
        )

        if not self.api_key:
            logger.warning("resend_api_key_missing", msg="RESEND_API_KEY not configured")

    async def send_email(
        self,
        *,
        from_email: str,
        to_emails: list[str],
        subject: str,
        html: str,
        text: str,
    ) -> ResendEmailResponse:
        """Send an email via Resend."""
        if not self.api_key:
            raise ResendClientError("RESEND_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": from_email,
            "to": to_emails,
            "subject": subject,
            "html": html,
            "text": text,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/emails",
                headers=headers,
                json=payload,
            )

        if response.status_code not in (200, 201):
            raise ResendAPIError(
                f"Resend error {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ResendAPIError(
                "Resend response was not valid JSON",
                status_code=response.status_code,
            ) from exc

        email_id = data.get("id")
        if not email_id:
            raise ResendAPIError(
                "Resend response missing email id",
                status_code=response.status_code,
            )

        return ResendEmailResponse(id=email_id)
