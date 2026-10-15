"""
Summary email service for assessment results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select
from src.core.config import get_settings
from src.domain.services.fusion import FusionService
from src.infrastructure.db.models import UserModel
from src.libs.resend_client import ResendClient, ResendClientError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class AssessmentResultNotReadyError(Exception):
    """Raised when assessment results are not ready for email delivery."""


class RecipientEmailMissingError(Exception):
    """Raised when recipient email is missing."""


class SummaryEmailSendError(Exception):
    """Raised when email delivery fails."""


@dataclass(slots=True)
class SummaryEmailResult:
    assessment_id: str
    to_email: str
    resend_id: str
    sent_at: str


class SummaryEmailService:
    """Service to send assessment summary emails via Resend."""

    def __init__(self, session: AsyncSession, client: ResendClient | None = None) -> None:
        self.session = session
        self.client = client or ResendClient()
        self.settings = get_settings()

    async def send_summary_email(
        self,
        *,
        assessment_id: str,
        user_id: str,
        user_email: str | None = None,
    ) -> SummaryEmailResult:
        """Send assessment summary and recommendation links to the user."""
        result = await FusionService(self.session).get_assessment_result(
            assessment_id=assessment_id,
            user_id=user_id,
        )

        if not result.get("summary"):
            raise AssessmentResultNotReadyError(
                "Assessment results are not ready for email delivery"
            )

        recipient_email = user_email or await self._get_user_email(user_id)
        if not recipient_email:
            raise RecipientEmailMissingError("User email address is missing")

        from_email = self.settings.resend_from_email
        if not from_email:
            raise SummaryEmailSendError("RESEND_FROM_EMAIL not configured")

        subject = "MicroCred Assessment Summary"
        text_body, html_body = self._build_email_content(result)

        try:
            response = await self.client.send_email(
                from_email=from_email,
                to_emails=[recipient_email],
                subject=subject,
                html=html_body,
                text=text_body,
            )
        except ResendClientError as exc:
            await logger.aerror(
                "summary_email_failed",
                assessment_id=assessment_id,
                user_id=user_id,
                error=str(exc),
            )
            raise SummaryEmailSendError("Failed to send summary email") from exc

        sent_at = datetime.now(UTC).isoformat()
        await logger.ainfo(
            "summary_email_sent",
            assessment_id=assessment_id,
            user_id=user_id,
            to_email=recipient_email,
            resend_id=response.id,
        )

        return SummaryEmailResult(
            assessment_id=assessment_id,
            to_email=recipient_email,
            resend_id=response.id,
            sent_at=sent_at,
        )

    async def _get_user_email(self, user_id: str) -> str | None:
        stmt = select(UserModel.email).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_email_content(self, result: dict) -> tuple[str, str]:
        summary = str(result.get("summary") or "").strip()
        recommendations = result.get("recommendations", []) or []

        text_lines = [
            "Hi,",
            "",
            "Here is your assessment summary:",
            "",
            summary if summary else "Summary not available.",
            "",
            "Recommended items:",
        ]

        if recommendations:
            for item in recommendations:
                title = str(item.get("course_title") or "Untitled")
                url = item.get("course_url")
                rank = item.get("rank")
                prefix = f"{rank}. " if rank is not None else "- "
                if url:
                    text_lines.append(f"{prefix}{title} - {url}")
                else:
                    text_lines.append(f"{prefix}{title}")
        else:
            text_lines.append("No recommendations available yet.")

        text_lines.extend(["", "Thank you,", "MicroCred Team"])
        text_body = "\n".join(text_lines)

        summary_html = escape(summary) if summary else "Summary not available."
        items_html = self._build_recommendations_html(recommendations)
        html_body = (
            "<p>Hi,</p>"
            "<p>Here is your assessment summary:</p>"
            f"<pre>{summary_html}</pre>"
            "<p>Recommended items:</p>"
            f"{items_html}"
            "<p>Thank you,<br>MicroCred Team</p>"
        )

        return text_body, html_body

    def _build_recommendations_html(self, recommendations: list[dict]) -> str:
        if not recommendations:
            return "<p>No recommendations available yet.</p>"

        items = []
        for item in recommendations:
            title = escape(str(item.get("course_title") or "Untitled"))
            url = item.get("course_url")
            if url:
                url_text = escape(str(url))
                items.append(f'<li><a href="{url_text}">{title}</a></li>')
            else:
                items.append(f"<li>{title}</li>")
        return "<ol>" + "".join(items) + "</ol>"
