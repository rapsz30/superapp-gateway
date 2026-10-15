"""
GPT Essay Scoring Service.

Story 2.2: Evaluates essays asynchronously via GPT with rubric-based scoring.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.db.models import (
    Assessment,
    AssessmentQuestionSnapshot,
    AssessmentResponse,
    AsyncJob,
    JobStatus,
    QuestionType,
    Score,
)
from src.libs.gpt_client import (
    GPTClientError,
    GPTClientProtocol,
    OpenAIClient,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

# Rubric dimensions for essay scoring
ESSAY_RUBRIC_DIMENSIONS = [
    "relevance",  # How relevant is the answer to the question
    "depth",  # Depth of analysis and understanding
    "clarity",  # Clarity of expression
    "completeness",  # Completeness of the answer
    "technical",  # Technical accuracy (if applicable)
]

DEFAULT_RUBRIC = {
    "dimensions": {
        "relevance": 0.2,
        "depth": 0.2,
        "clarity": 0.2,
        "completeness": 0.2,
        "technical": 0.2,
    },
    "floor": 0,
    "ceiling": 95,
}

DIFFICULTY_RUBRICS: dict[str, dict[str, object]] = {
    "easy": {
        "dimensions": {
            "relevance": 0.3,
            "clarity": 0.25,
            "completeness": 0.25,
            "depth": 0.1,
            "technical": 0.1,
        },
        "floor": 10,
        "ceiling": 95,
    },
    "medium": {
        "dimensions": {
            "relevance": 0.25,
            "clarity": 0.2,
            "completeness": 0.2,
            "depth": 0.2,
            "technical": 0.15,
        },
        "floor": 5,
        "ceiling": 95,
    },
    "hard": {
        "dimensions": {
            "relevance": 0.2,
            "clarity": 0.15,
            "completeness": 0.15,
            "depth": 0.25,
            "technical": 0.25,
        },
        "floor": 0,
        "ceiling": 95,
    },
}

# System prompt for deterministic essay scoring
ESSAY_SCORING_SYSTEM_PROMPT = """You are a strict essay evaluator for a micro-credential \
assessment platform.

Evaluation constraints:
- You are an evaluator, not a tutor.
- Use only the provided question, student answer, and reference answer in the prompt.
- Do not use external knowledge.
- Do not provide suggestions, feedback format, markdown, or prose outside JSON.

Rubric dimensions (0-100):
- relevance: How well the answer addresses the question
- depth: Depth of analysis and understanding
- clarity: Clarity and organization of expression
- completeness: Coverage of the asked scope
- technical: Technical correctness and terminology usage

Output contract (single JSON object only):
{
  "scores": {
    "relevance": <number>,
    "depth": <number>,
    "clarity": <number>,
    "completeness": <number>,
    "technical": <number>
  },
  "total_score": <number>,
  "explanation": "<short rationale linked to rubric>"
}
"""

JSON_ONLY_RETRY_PROMPT = """Return one valid JSON object only, matching the required schema exactly.
Do not add markdown, comments, or any extra text."""


@dataclass(slots=True)
class EssayScoreResult:
    """Result of scoring a single essay."""

    question_snapshot_id: str
    score: float
    max_score: float
    rubric_scores: dict[str, float]
    rubric_weights: dict[str, float]
    normalized_score: float
    explanation: str
    model: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    scoring_method: str = "gpt"
    parse_recovery_used: bool = False
    parse_attempt_count: int = 1
    retry_used: bool = False
    retry_count: int = 0


@dataclass(slots=True)
class EssayScoringResult:
    """Result of scoring all essays in an assessment."""

    assessment_id: str
    essay_scores: list[EssayScoreResult]
    total_score: float
    max_score: float
    status: str  # "success" or "partial" or "failed"
    failed_count: int
    fallback_count: int = 0
    hard_failed_count: int = 0
    parse_error_count: int = 0
    parse_recovery_count: int = 0
    retry_used_count: int = 0
    error_details: list[dict[str, str]] | None = None
    error_message: str | None = None


class GPTScoringError(Exception):
    """Raised when GPT scoring fails."""

    def __init__(
        self,
        message: str,
        question_id: str | None = None,
        *,
        retry_used: bool = False,
        parse_attempt_count: int = 0,
    ):
        super().__init__(message)
        self.question_id = question_id
        self.retry_used = retry_used
        self.parse_attempt_count = parse_attempt_count


class GPTEssayScoringService:
    """
    Service for scoring essays using GPT.

    AC1: Batches essays per assessment and calls GPT with deterministic prompt.
    AC2: Parses GPT responses into rubric metrics.
    AC3: Retries up to three attempts with exponential backoff.
    """

    MAX_SCORE = 100.0

    def __init__(
        self,
        session: AsyncSession,
        gpt_client: GPTClientProtocol | None = None,
    ) -> None:
        self.session = session
        self.gpt_client = gpt_client or OpenAIClient()

    async def score_assessment_essays(
        self,
        assessment_id: str,
        job_id: str,
    ) -> EssayScoringResult:
        """
        Score all essay responses for an assessment.

        AC1: Worker pulls essays and calls GPT with deterministic prompt.
        AC2: GPT responses parsed into rubric metrics.
        AC3: Failures logged and job marked failed.
        """
        # Update job status to in_progress
        await self._update_job_status(
            job_id,
            JobStatus.IN_PROGRESS,
            progress_percentage=5.0,
            progress_step="Preparing essay scoring",
        )

        try:
            # Get assessment with essay responses
            essays = await self._get_essay_responses(assessment_id)

            if not essays:
                await logger.ainfo(
                    "no_essays_to_score",
                    assessment_id=assessment_id,
                )
                await self._update_job_status(
                    job_id,
                    JobStatus.COMPLETED,
                    progress_percentage=100.0,
                    progress_step="No essays to score",
                )
                return EssayScoringResult(
                    assessment_id=assessment_id,
                    essay_scores=[],
                    total_score=0.0,
                    max_score=0.0,
                    status="success",
                    failed_count=0,
                )

            # Score each essay
            results: list[EssayScoreResult] = []
            failed_count = 0
            fallback_count = 0
            hard_failed_count = 0
            parse_error_count = 0
            parse_recovery_count = 0
            retry_used_count = 0
            error_details: list[dict[str, str]] = []

            total_essays = len(essays)
            for index, (snapshot, response) in enumerate(essays, start=1):
                try:
                    score_result = await self._score_single_essay(
                        snapshot=snapshot,
                        response=response,
                    )
                    if score_result.parse_recovery_used:
                        parse_recovery_count += 1
                    if score_result.retry_used:
                        retry_used_count += score_result.retry_count or 1
                    results.append(score_result)

                    # Save score to database
                    await self._save_essay_score(assessment_id, score_result)

                except (GPTScoringError, GPTClientError) as e:
                    failed_count += 1
                    is_parse_error = isinstance(e, GPTScoringError) and str(e).lower().startswith(
                        "failed to parse gpt response",
                    )
                    retry_used = isinstance(e, GPTScoringError) and bool(e.retry_used)
                    if retry_used:
                        retry_used_count += 1
                    if is_parse_error:
                        parse_error_count += 1
                    error_detail = {
                        "question_id": snapshot.id,
                        "error_type": type(e).__name__,
                        "message": str(e),
                        "is_parse_error": str(is_parse_error).lower(),
                        "retry_used": str(retry_used).lower(),
                        "parse_attempt_count": str(
                            e.parse_attempt_count if isinstance(e, GPTScoringError) else 0,
                        ),
                    }
                    error_details.append(error_detail)
                    await logger.aerror(
                        "essay_scoring_failed",
                        assessment_id=assessment_id,
                        question_id=snapshot.id,
                        error=str(e),
                    )
                    try:
                        fallback_result = self._build_fallback_score(
                            snapshot=snapshot,
                            response=response,
                            reason=str(e),
                        )
                        fallback_count += 1
                        results.append(fallback_result)
                        await self._save_essay_score(assessment_id, fallback_result)
                        await logger.awarning(
                            "essay_scoring_fallback_used",
                            assessment_id=assessment_id,
                            question_id=snapshot.id,
                        )
                    except Exception as fallback_error:
                        hard_failed_count += 1
                        error_detail["fallback_error"] = str(fallback_error)
                        await logger.aerror(
                            "essay_scoring_fallback_failed",
                            assessment_id=assessment_id,
                            question_id=snapshot.id,
                            error=str(fallback_error),
                        )

                # Persist real-time progress for status polling.
                progress_percentage = 10.0 + (index / max(total_essays, 1)) * 80.0
                await self._update_job_progress(
                    job_id,
                    progress_percentage=progress_percentage,
                    progress_step=f"Scored essay {index}/{total_essays}",
                )

            # Calculate totals
            total_score = sum(r.score for r in results) if results else 0.0
            max_score = sum(self.MAX_SCORE * (snapshot.weight or 1.0) for snapshot, _ in essays)

            # Determine status
            if failed_count == 0 and hard_failed_count == 0:
                status = "success"
            elif hard_failed_count < len(essays):
                status = "partial"
            else:
                status = "failed"

            # Update job status
            job_status = JobStatus.COMPLETED if hard_failed_count == 0 else JobStatus.FAILED
            error_payload = self._build_job_error_payload(
                failed_count=failed_count,
                fallback_count=fallback_count,
                hard_failed_count=hard_failed_count,
                parse_error_count=parse_error_count,
                retry_used_count=retry_used_count,
                errors=error_details,
            )
            await self._update_job_status(
                job_id,
                job_status,
                error_payload=error_payload,
                progress_percentage=100.0 if job_status == JobStatus.COMPLETED else 95.0,
                progress_step="Completed" if job_status == JobStatus.COMPLETED else "Failed",
            )

            # If any failures, mark assessment as degraded
            if failed_count > 0:
                await self._mark_assessment_degraded(assessment_id)

            # Log completion
            await logger.ainfo(
                "essay_scoring_completed",
                assessment_id=assessment_id,
                scored_count=len(results),
                failed_count=failed_count,
                fallback_count=fallback_count,
                hard_failed_count=hard_failed_count,
                parse_error_count=parse_error_count,
                parse_recovery_count=parse_recovery_count,
                retry_used_count=retry_used_count,
                total_score=total_score,
                max_score=max_score,
            )

            return EssayScoringResult(
                assessment_id=assessment_id,
                essay_scores=results,
                total_score=total_score,
                max_score=max_score,
                status=status,
                failed_count=failed_count,
                fallback_count=fallback_count,
                hard_failed_count=hard_failed_count,
                parse_error_count=parse_error_count,
                parse_recovery_count=parse_recovery_count,
                retry_used_count=retry_used_count,
                error_details=error_details[:10] if error_details else None,
            )

        except Exception as e:
            # Unexpected error - mark job failed
            await logger.aerror(
                "essay_scoring_unexpected_error",
                assessment_id=assessment_id,
                error=str(e),
            )
            await self._update_job_status(
                job_id,
                JobStatus.FAILED,
                error_payload={"error": str(e)},
                progress_percentage=95.0,
                progress_step="Failed",
            )
            await self._mark_assessment_degraded(assessment_id)
            raise

    async def _get_essay_responses(
        self,
        assessment_id: str,
    ) -> list[tuple[AssessmentQuestionSnapshot, AssessmentResponse]]:
        """Get all essay questions and responses for an assessment."""
        stmt = (
            select(AssessmentQuestionSnapshot, AssessmentResponse)
            .join(
                AssessmentResponse,
                AssessmentResponse.question_snapshot_id == AssessmentQuestionSnapshot.id,
            )
            .where(
                AssessmentQuestionSnapshot.assessment_id == assessment_id,
                AssessmentQuestionSnapshot.question_type == QuestionType.ESSAY,
            )
            .order_by(AssessmentQuestionSnapshot.sequence)
        )
        result = await self.session.execute(stmt)
        return list(result.all())

    async def _score_single_essay(
        self,
        snapshot: AssessmentQuestionSnapshot,
        response: AssessmentResponse,
    ) -> EssayScoreResult:
        """Score a single essay using GPT."""
        # Build user prompt
        essay_text = response.response_data.get("answer", "")
        max_score = self.MAX_SCORE * (snapshot.weight or 1.0)
        rubric = self._resolve_rubric(snapshot)
        if not essay_text:
            # No answer provided - give zero score
            return EssayScoreResult(
                question_snapshot_id=snapshot.id,
                score=0.0,
                max_score=max_score,
                rubric_scores={dim: 0.0 for dim in ESSAY_RUBRIC_DIMENSIONS},
                rubric_weights=rubric["dimensions"],
                normalized_score=0.0,
                explanation="No answer provided.",
                model="rule",
                latency_ms=0,
                prompt_tokens=0,
                completion_tokens=0,
                scoring_method="rule",
            )
        if self._is_non_informative_essay(essay_text):
            # Prevent nonsense answers from receiving rubric floor points.
            return EssayScoreResult(
                question_snapshot_id=snapshot.id,
                score=0.0,
                max_score=max_score,
                rubric_scores={dim: 0.0 for dim in ESSAY_RUBRIC_DIMENSIONS},
                rubric_weights=rubric["dimensions"],
                normalized_score=0.0,
                explanation="Answer is too short or non-informative for essay evaluation.",
                model="rule",
                latency_ms=0,
                prompt_tokens=0,
                completion_tokens=0,
                scoring_method="rule",
            )

        answer_key = snapshot.model_answer or snapshot.answer_key or ""
        rubric_weights = rubric["dimensions"]
        rubric_lines = [f"- {dim}: weight {weight:.2f}" for dim, weight in rubric_weights.items()]
        reference_section = (
            f"\nReference answer (for rubric alignment):\n{answer_key}\n" if answer_key else ""
        )
        rubric_section = (
            "\nRubric weights:\n" + "\n".join(rubric_lines) + "\n" if rubric_weights else ""
        )

        user_prompt = f"""Question: {snapshot.prompt}

Student's Essay Answer:
{essay_text}

Please score this essay according to the rubric dimensions.{reference_section}{rubric_section}"""

        messages = [
            {"role": "system", "content": ESSAY_SCORING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # Call GPT (network/client retries handled by client)
        gpt_response = await self.gpt_client.chat_completion(
            messages=messages,
            temperature=0.0,
            max_tokens=500,
        )

        retry_used = False
        retry_count = 0
        total_parse_attempt_count = 0
        parse_recovery_used = False

        # Parse response with one deterministic re-ask before failing
        try:
            (
                parsed,
                parse_recovery_used_first,
                parse_attempt_count_first,
            ) = self._parse_gpt_response_with_recovery(gpt_response.content)
            total_parse_attempt_count += parse_attempt_count_first
            parse_recovery_used = parse_recovery_used_first
        except Exception as first_parse_error:
            total_parse_attempt_count += 1
            retry_used = True
            retry_count = 1

            retry_messages = self._build_json_retry_messages(
                messages=messages,
                prior_response=gpt_response.content,
            )
            retry_response = await self.gpt_client.chat_completion(
                messages=retry_messages,
                temperature=0.0,
                max_tokens=500,
            )

            try:
                (
                    parsed,
                    parse_recovery_used_retry,
                    parse_attempt_count_retry,
                ) = self._parse_gpt_response_with_recovery(retry_response.content)
                total_parse_attempt_count += parse_attempt_count_retry
                parse_recovery_used = parse_recovery_used or parse_recovery_used_retry
                gpt_response = retry_response
            except Exception as retry_parse_error:
                total_parse_attempt_count += 1
                raise GPTScoringError(
                    f"Failed to parse GPT response: {first_parse_error}; "
                    f"retry_failed: {retry_parse_error}",
                    question_id=snapshot.id,
                    retry_used=True,
                    parse_attempt_count=total_parse_attempt_count,
                ) from retry_parse_error

        weighted_total = self._apply_rubric_weights(parsed["scores"], rubric)
        normalized_total = self._apply_floor_ceiling(weighted_total, rubric)
        scaled_total = normalized_total * (snapshot.weight or 1.0)

        return EssayScoreResult(
            question_snapshot_id=snapshot.id,
            score=scaled_total,
            max_score=max_score,
            rubric_scores=parsed["scores"],
            rubric_weights=rubric["dimensions"],
            normalized_score=normalized_total,
            explanation=parsed["explanation"],
            model=gpt_response.model,
            latency_ms=gpt_response.latency_ms,
            prompt_tokens=gpt_response.prompt_tokens,
            completion_tokens=gpt_response.completion_tokens,
            parse_recovery_used=parse_recovery_used,
            parse_attempt_count=max(total_parse_attempt_count, 1),
            retry_used=retry_used,
            retry_count=retry_count,
        )

    def _resolve_rubric(self, snapshot: AssessmentQuestionSnapshot) -> dict[str, Any]:
        rubric = snapshot.rubric or {}
        difficulty = (snapshot.difficulty or "medium").lower()
        base = DIFFICULTY_RUBRICS.get(difficulty, DEFAULT_RUBRIC)
        if not rubric:
            rubric = base
        rubric = {
            "dimensions": rubric.get("dimensions", base["dimensions"]),
            "floor": rubric.get("floor", base["floor"]),
            "ceiling": rubric.get("ceiling", base["ceiling"]),
        }

        weights = {}
        for dim in ESSAY_RUBRIC_DIMENSIONS:
            weights[dim] = float(rubric["dimensions"].get(dim, 0.0))
        total = sum(weights.values())
        if total <= 0:
            weights = {dim: 1.0 / len(ESSAY_RUBRIC_DIMENSIONS) for dim in ESSAY_RUBRIC_DIMENSIONS}
        else:
            weights = {dim: weight / total for dim, weight in weights.items()}
        rubric["dimensions"] = weights
        return rubric

    @staticmethod
    def _apply_rubric_weights(scores: dict[str, float], rubric: dict[str, Any]) -> float:
        total = 0.0
        for dim, weight in rubric["dimensions"].items():
            total += scores.get(dim, 0.0) * weight
        return total

    @staticmethod
    def _apply_floor_ceiling(score: float, rubric: dict[str, Any]) -> float:
        floor = float(rubric.get("floor", 0))
        ceiling = float(rubric.get("ceiling", 100))
        return max(floor, min(ceiling, score))

    def _parse_gpt_response_with_recovery(self, content: str) -> tuple[dict[str, Any], bool, int]:
        """
        Parse GPT response with recovery attempts before failing to fallback.

        Returns parsed payload, whether recovery was needed, and parse attempt count.
        """
        candidates = self._build_json_parse_candidates(content)
        if not candidates:
            raise ValueError("No JSON parse candidates found in GPT response")

        parse_errors: list[str] = []
        for attempt, candidate in enumerate(candidates, start=1):
            try:
                parsed = self._parse_gpt_json_payload(candidate)
                return parsed, attempt > 1, attempt
            except ValueError as exc:
                parse_errors.append(str(exc))

        last_error = parse_errors[-1] if parse_errors else "unknown parse error"
        raise ValueError(
            "Failed to parse GPT response after recovery attempts: " f"{last_error}",
        )

    def _parse_gpt_response(self, content: str) -> dict[str, Any]:
        """Strict parser for GPT response JSON."""
        extracted = self._extract_json_object(content)
        return self._parse_gpt_json_payload(extracted)

    def _parse_gpt_json_payload(self, payload: str) -> dict[str, Any]:
        """Parse and validate a JSON payload string for essay rubric scores."""
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in GPT response: {e}") from e

        # Validate structure
        if "scores" not in data and not all(dim in data for dim in ESSAY_RUBRIC_DIMENSIONS):
            raise ValueError("Missing required fields in GPT response")

        raw_scores = data["scores"] if "scores" in data else data
        if not isinstance(raw_scores, dict):
            raise ValueError("GPT response 'scores' must be an object")
        scores = raw_scores.copy()
        for dim in ESSAY_RUBRIC_DIMENSIONS:
            if dim not in scores:
                scores[dim] = 0.0
            else:
                # Clamp to 0-100
                scores[dim] = max(0.0, min(100.0, float(scores[dim])))

        total_score_raw = data.get("total_score")
        if total_score_raw is None:
            total_score_raw = sum(scores.values()) / len(ESSAY_RUBRIC_DIMENSIONS)

        return {
            "scores": scores,
            "total_score": max(0.0, min(100.0, float(total_score_raw))),
            "explanation": data.get("explanation", ""),
        }

    def _build_json_parse_candidates(self, content: str) -> list[str]:
        """Build unique strict + repaired JSON candidates from GPT content."""
        cleaned = str(content or "").strip()
        if not cleaned:
            return []

        base_payload: str | None = None
        try:
            base_payload = self._extract_json_object(cleaned)
        except ValueError as exc:
            partial = self._extract_partial_json_object(cleaned)
            if partial is None:
                raise exc
            base_payload = partial

        candidates: list[str] = []

        def _append(payload: str | None) -> None:
            if not payload:
                return
            normalized = payload.strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        _append(base_payload)

        sanitized = self._sanitize_json_payload(base_payload)
        _append(sanitized)

        no_trailing_commas = self._remove_trailing_commas(base_payload)
        _append(no_trailing_commas)

        balanced = self._close_unterminated_json(base_payload)
        _append(balanced)

        repaired = self._close_unterminated_json(self._remove_trailing_commas(sanitized))
        _append(repaired)
        return candidates

    @staticmethod
    def _build_json_retry_messages(
        messages: list[dict[str, str]],
        prior_response: str,
    ) -> list[dict[str, str]]:
        """Build one retry prompt that requests strict JSON-only output."""
        retry_messages = list(messages)
        retry_messages.append({"role": "assistant", "content": str(prior_response)})
        retry_messages.append({"role": "user", "content": JSON_ONLY_RETRY_PROMPT})
        return retry_messages

    @staticmethod
    def _extract_partial_json_object(content: str) -> str | None:
        """Return a best-effort JSON substring when object is unterminated."""
        start = content.find("{")
        if start == -1:
            return None
        partial = content[start:].strip()
        return partial or None

    @staticmethod
    def _sanitize_json_payload(payload: str) -> str:
        """Normalize common unicode quotes and whitespace before parsing."""
        sanitized = payload.replace("\u201c", '"').replace("\u201d", '"')
        sanitized = sanitized.replace("\u2018", "'").replace("\u2019", "'")
        return sanitized.strip()

    @staticmethod
    def _remove_trailing_commas(payload: str) -> str:
        """Remove trailing commas before object/array closure."""
        return re.sub(r",\s*([}\]])", r"\1", payload)

    @staticmethod
    def _close_unterminated_json(payload: str) -> str:
        """Append missing closing delimiters for truncated JSON objects/arrays."""
        text = payload.rstrip()
        depth_object = 0
        depth_array = 0
        in_string = False
        escape_next = False
        for char in text:
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth_object += 1
            elif char == "}":
                depth_object = max(0, depth_object - 1)
            elif char == "[":
                depth_array += 1
            elif char == "]":
                depth_array = max(0, depth_array - 1)

        if in_string:
            text += '"'
        if depth_array > 0:
            text += "]" * depth_array
        if depth_object > 0:
            text += "}" * depth_object
        return text

    def _extract_json_object(self, content: str) -> str:
        """Extract JSON payload from plain text or markdown response."""
        cleaned = content.strip()
        if not cleaned:
            raise ValueError("Empty GPT response")

        fenced_match = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fenced_match:
            cleaned = fenced_match.group(1).strip()
            if cleaned:
                return cleaned

        if cleaned.startswith("{") and cleaned.endswith("}"):
            return cleaned

        start = cleaned.find("{")
        if start == -1:
            raise ValueError("No JSON object found in GPT response")

        depth = 0
        in_string = False
        escape_next = False
        for idx, char in enumerate(cleaned[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return cleaned[start : idx + 1]

        raise ValueError("Unterminated JSON object in GPT response")

    def _build_fallback_score(
        self,
        snapshot: AssessmentQuestionSnapshot,
        response: AssessmentResponse,
        reason: str,
    ) -> EssayScoreResult:
        """Generate deterministic fallback score when GPT is unavailable."""
        essay_text = str(response.response_data.get("answer", "")).strip()
        rubric = self._resolve_rubric(snapshot)
        max_score = self.MAX_SCORE * (snapshot.weight or 1.0)
        if self._is_non_informative_essay(essay_text):
            return EssayScoreResult(
                question_snapshot_id=snapshot.id,
                score=0.0,
                max_score=max_score,
                rubric_scores={dim: 0.0 for dim in ESSAY_RUBRIC_DIMENSIONS},
                rubric_weights=rubric["dimensions"],
                normalized_score=0.0,
                explanation=(
                    "Fallback scoring applied: answer is too short or non-informative "
                    f"({reason})."
                ),
                model="rule-fallback",
                latency_ms=0,
                prompt_tokens=0,
                completion_tokens=0,
                scoring_method="rule_fallback",
            )

        tokens = re.findall(r"[A-Za-z0-9']+", essay_text.lower())
        token_count = len(tokens)

        if token_count < 10:
            base = 25.0
        elif token_count < 25:
            base = 40.0
        elif token_count < 60:
            base = 55.0
        elif token_count < 120:
            base = 68.0
        else:
            base = 78.0

        answer_key = (snapshot.model_answer or snapshot.answer_key or "").lower()
        key_terms = {token for token in re.findall(r"[A-Za-z0-9']+", answer_key) if len(token) >= 4}
        response_terms = set(tokens)
        overlap_ratio = (
            (len(key_terms & response_terms) / min(len(key_terms), 20)) if key_terms else 0.0
        )
        keyword_bonus = min(12.0, overlap_ratio * 12.0)

        rubric_scores = {
            "relevance": max(0.0, min(100.0, base + keyword_bonus)),
            "depth": max(0.0, min(100.0, base - 5.0 + (token_count / 30))),
            "clarity": max(0.0, min(100.0, base)),
            "completeness": max(0.0, min(100.0, base - 3.0 + keyword_bonus / 2)),
            "technical": max(0.0, min(100.0, base - 4.0 + keyword_bonus)),
        }

        weighted_total = self._apply_rubric_weights(rubric_scores, rubric)
        normalized_total = self._apply_floor_ceiling(weighted_total, rubric)
        scaled_total = normalized_total * (snapshot.weight or 1.0)

        return EssayScoreResult(
            question_snapshot_id=snapshot.id,
            score=scaled_total,
            max_score=max_score,
            rubric_scores=rubric_scores,
            rubric_weights=rubric["dimensions"],
            normalized_score=normalized_total,
            explanation=f"Fallback scoring applied because GPT is unavailable: {reason}",
            model="rule-fallback",
            latency_ms=0,
            prompt_tokens=0,
            completion_tokens=0,
            scoring_method="rule_fallback",
        )

    @staticmethod
    def _is_non_informative_essay(essay_text: str) -> bool:
        """Detect very short/repetitive answers that should receive zero score."""
        cleaned = str(essay_text or "").strip().lower()
        if not cleaned:
            return True

        tokens = re.findall(r"[A-Za-z0-9']+", cleaned)
        if len(tokens) <= 2:
            return True

        unique_tokens = set(tokens)
        if len(tokens) < 8 and len(unique_tokens) <= 2:
            return True

        # Examples: "aaaa", "11111", "bbbbbb"
        if re.fullmatch(r"(.)\1{3,}", cleaned):
            return True

        return False

    @staticmethod
    def _build_job_error_payload(
        failed_count: int,
        fallback_count: int,
        hard_failed_count: int,
        parse_error_count: int,
        retry_used_count: int,
        errors: list[dict[str, str]],
    ) -> dict[str, Any] | None:
        if failed_count == 0 and hard_failed_count == 0:
            return None

        if hard_failed_count > 0:
            message = "GPT scoring failed for one or more essays."
        else:
            message = "GPT scoring used fallback scoring for one or more essays."

        return {
            "message": message,
            "failed_count": failed_count,
            "fallback_count": fallback_count,
            "hard_failed_count": hard_failed_count,
            "parse_error_count": parse_error_count,
            "retry_used_count": retry_used_count,
            "errors": errors[:10],
        }

    async def _save_essay_score(
        self,
        assessment_id: str,
        result: EssayScoreResult,
    ) -> None:
        """Save essay score to database."""
        existing_stmt = select(Score).where(
            Score.assessment_id == assessment_id,
            Score.question_snapshot_id == result.question_snapshot_id,
            Score.question_type == QuestionType.ESSAY,
        )
        existing_score = (await self.session.execute(existing_stmt)).scalar_one_or_none()

        payload_rules = {
            "rubric_scores": result.rubric_scores,
            "rubric_weights": result.rubric_weights,
            "normalized_score": result.normalized_score,
        }
        payload_model = {
            "model": result.model,
            "latency_ms": result.latency_ms,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "parse_recovery_used": result.parse_recovery_used,
            "parse_attempt_count": result.parse_attempt_count,
            "retry_used": result.retry_used,
            "retry_count": result.retry_count,
        }

        if existing_score:
            existing_score.score = result.score
            existing_score.max_score = result.max_score
            existing_score.explanation = result.explanation
            existing_score.scoring_method = result.scoring_method
            existing_score.rules_applied = payload_rules
            existing_score.model_info = payload_model
        else:
            score = Score(
                assessment_id=assessment_id,
                question_snapshot_id=result.question_snapshot_id,
                question_type=QuestionType.ESSAY,
                score=result.score,
                max_score=result.max_score,
                explanation=result.explanation,
                scoring_method=result.scoring_method,
                rules_applied=payload_rules,
                model_info=payload_model,
            )
            self.session.add(score)
        await self.session.flush()

    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error_payload: dict[str, Any] | None = None,
        *,
        progress_percentage: float | None = None,
        progress_step: str | None = None,
    ) -> None:
        """Update async job status."""
        values: dict[str, Any] = {"status": status}

        if status == JobStatus.IN_PROGRESS:
            values["started_at"] = datetime.now(UTC)
            values["attempts"] = AsyncJob.attempts + 1
        elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
            values["completed_at"] = datetime.now(UTC)

        if error_payload is not None:
            values["error_payload"] = error_payload
        elif status in (JobStatus.IN_PROGRESS, JobStatus.COMPLETED):
            values["error_payload"] = None

        payload = await self._get_job_payload(job_id)
        default_step = (
            "Scoring essays"
            if status == JobStatus.IN_PROGRESS
            else "Completed"
            if status == JobStatus.COMPLETED
            else "Failed"
            if status == JobStatus.FAILED
            else None
        )
        default_progress = (
            5.0
            if status == JobStatus.IN_PROGRESS
            else 100.0
            if status == JobStatus.COMPLETED
            else progress_percentage
        )
        merged_payload = self._merge_progress_payload(
            payload,
            progress_percentage=(
                default_progress if progress_percentage is None else progress_percentage
            ),
            progress_step=progress_step if progress_step is not None else default_step,
        )
        values["payload"] = merged_payload

        await self.session.execute(update(AsyncJob).where(AsyncJob.id == job_id).values(**values))
        await self.session.commit()

    async def _update_job_progress(
        self,
        job_id: str,
        *,
        progress_percentage: float,
        progress_step: str | None = None,
    ) -> None:
        """Update progress payload without changing status."""
        payload = await self._get_job_payload(job_id)
        merged_payload = self._merge_progress_payload(
            payload,
            progress_percentage=progress_percentage,
            progress_step=progress_step,
        )
        await self.session.execute(
            update(AsyncJob).where(AsyncJob.id == job_id).values(payload=merged_payload)
        )
        await self.session.commit()

    async def _get_job_payload(self, job_id: str) -> dict[str, Any]:
        stmt = select(AsyncJob.payload).where(AsyncJob.id == job_id)
        result = await self.session.execute(stmt)
        payload = result.scalar_one_or_none()
        return payload.copy() if isinstance(payload, dict) else {}

    def _merge_progress_payload(
        self,
        payload: dict[str, Any],
        *,
        progress_percentage: float | None = None,
        progress_step: str | None = None,
    ) -> dict[str, Any]:
        merged = payload.copy() if isinstance(payload, dict) else {}
        progress = merged.get("progress")
        if not isinstance(progress, dict):
            progress = {}

        if isinstance(progress_percentage, int | float):
            progress["percentage"] = round(max(0.0, min(float(progress_percentage), 100.0)), 1)
        if isinstance(progress_step, str):
            cleaned_step = progress_step.strip()
            if cleaned_step:
                progress["step"] = cleaned_step

        progress["updated_at"] = datetime.now(UTC).isoformat()
        merged["progress"] = progress
        return merged

    async def _mark_assessment_degraded(self, assessment_id: str) -> None:
        """Mark assessment as degraded due to scoring failures."""
        await self.session.execute(
            update(Assessment).where(Assessment.id == assessment_id).values(degraded=True)
        )
        await self.session.commit()
