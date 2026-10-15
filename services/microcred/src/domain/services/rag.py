"""
RAG Service for Story 3.1: Role-Aware RAG Retrieval.

Uses TF-IDF based retrieval from Udemy courses dataset as a simple RAG implementation.
Can be upgraded to Chroma/PGVector for production.
"""

from __future__ import annotations

import ast
import csv
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import delete, select
from src.infrastructure.db.models import (
    Assessment,
    AssessmentQuestionSnapshot,
    AssessmentResponse,
    AsyncJob,
    JobStatus,
    JobType,
    QuestionType,
    Recommendation,
    RecommendationItem,
    RoleCatalog,
    Score,
)
from src.infrastructure.repositories.course_enrichment import (
    TECH_KEYWORD_MAP,
    CourseEnricher,
    EnrichedCourseMetadata,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Path to courses dataset
COURSES_CSV_PATH = (
    Path(__file__).parent.parent.parent / "infrastructure/repositories/udemy_courses.csv"
)

# Role to subject/keyword mappings for better retrieval
ROLE_KEYWORDS: dict[str, list[str]] = {
    "backend-engineer": [
        "python",
        "java",
        "node",
        "api",
        "database",
        "sql",
        "backend",
        "server",
        "microservices",
        "django",
        "flask",
        "spring",
        "aws",
    ],
    "frontend-engineer": [
        "javascript",
        "react",
        "vue",
        "angular",
        "css",
        "html",
        "frontend",
        "web development",
        "typescript",
        "ui",
        "ux",
    ],
    "data-scientist": [
        "python",
        "machine learning",
        "data science",
        "statistics",
        "pandas",
        "numpy",
        "tensorflow",
        "deep learning",
        "ai",
        "analytics",
    ],
    "data-analyst": [
        "sql",
        "excel",
        "power bi",
        "tableau",
        "data analysis",
        "data analytics",
        "statistics",
        "python",
        "pandas",
        "visualization",
        "dashboard",
        "business intelligence",
    ],
    "devops-engineer": [
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "devops",
        "ci/cd",
        "jenkins",
        "terraform",
        "ansible",
        "linux",
        "cloud",
    ],
    "product-manager": [
        "product management",
        "agile",
        "scrum",
        "business",
        "strategy",
        "roadmap",
        "user research",
        "analytics",
    ],
}

ROLE_FOUNDATION_KEYWORDS: dict[str, list[str]] = {
    "backend-engineer": [
        "programming fundamentals",
        "python",
        "api",
        "rest",
        "database",
        "sql",
        "backend basics",
    ],
    "data-analyst": [
        "data analysis fundamentals",
        "sql",
        "excel",
        "statistics",
        "data visualization",
        "dashboard",
    ],
}

ROLE_SUBJECTS: dict[str, list[str]] = {
    "backend-engineer": ["Web Development"],
    "frontend-engineer": ["Web Development"],
    "devops-engineer": ["Web Development"],
    "data-analyst": ["Business Finance", "Web Development"],
    "data-scientist": ["Business Finance", "Web Development"],
    "product-manager": ["Business Finance"],
}

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "api": ["api", "rest", "graphql"],
    "database": ["database", "sql", "postgres", "mysql"],
    "performance": ["cache", "caching", "performance"],
    "testing": ["test", "testing", "pytest", "unit"],
    "backend": ["backend", "server", "node", "python", "go", "java"],
    "cloud": ["aws", "gcp", "azure", "cloud", "docker", "kubernetes"],
    "data": ["data", "analytics", "statistics", "sql"],
    "visualization": ["visualization", "dashboard", "tableau", "powerbi", "power"],
}

STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "to",
    "of",
    "in",
    "a",
    "on",
    "an",
    "your",
    "how",
    "what",
    "why",
    "is",
    "are",
    "this",
    "that",
}

# Technologies that usually require stronger fundamentals before advanced tracks.
ADVANCED_TECH_KEYWORDS = {
    "kubernetes",
    "microservices",
    "terraform",
    "aws",
    "azure",
    "gcp",
    "cloud",
    "devops",
    "kafka",
    "graphql",
    "machine learning",
    "deep learning",
}

INTERMEDIATE_TECH_KEYWORDS = {
    "redis",
    "docker",
    "ci/cd",
    "unit testing",
    "testing",
    "oauth",
    "jwt",
    "websocket",
    "message queue",
}

FOUNDATION_TECH_KEYWORDS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "sql",
    "html",
    "css",
    "git",
    "rest",
    "api",
    "oop",
    "algorithm",
    "data structure",
}


@dataclass
class CourseMatch:
    """A matched course from RAG retrieval."""

    course_id: str
    title: str
    url: str | None
    relevance_score: float
    match_reason: str
    metadata: dict


@dataclass
class RAGResult:
    """Result from RAG retrieval."""

    query: str
    matches: list[CourseMatch]
    degraded: bool = False
    error: str | None = None
    readiness: dict | None = None


class RAGRetrievalError(Exception):
    """Raised when RAG retrieval fails."""


class RAGService:
    """Service for RAG-based credential recommendations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._courses: list[dict] | None = None
        self._enriched_courses: dict[str, EnrichedCourseMetadata] = {}  # Cache enriched metadata

    @staticmethod
    def _parse_non_negative_int(value: object) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, float):
            return int(value) if value >= 0 else None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                parsed = int(stripped)
                return parsed if parsed >= 0 else None
        return None

    @staticmethod
    def _clean_text_list(value: object) -> list[str]:
        if isinstance(value, list | tuple | set):
            raw_items = value
        elif value is None:
            raw_items = []
        else:
            raw_items = [value]

        cleaned: list[str] = []
        for item in raw_items:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned

    @classmethod
    def _extract_project_profile_payload(
        cls,
        response_data: dict,
    ) -> tuple[int | None, list[str]]:
        project_count = cls._parse_non_negative_int(response_data.get("project_count"))
        contexts = cls._clean_text_list(response_data.get("selected_options"))

        if not contexts:
            contexts = cls._clean_text_list(response_data.get("project_contexts"))

        value = response_data.get("value")
        if isinstance(value, dict):
            if project_count is None:
                project_count = cls._parse_non_negative_int(value.get("project_count"))
            if not contexts:
                contexts = cls._clean_text_list(
                    value.get("selected_options") or value.get("project_contexts")
                )
        elif isinstance(value, list) and not contexts:
            contexts = cls._clean_text_list(value)
        elif project_count is None and not isinstance(value, list | dict):
            project_count = cls._parse_non_negative_int(value)

        return project_count, contexts

    def _load_courses(self) -> list[dict]:
        """Load courses from CSV file and enrich with comprehensive metadata."""
        if self._courses is not None:
            return self._courses

        courses = []
        try:
            with open(COURSES_CSV_PATH, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Legacy annotation for backward compatibility
                    self._annotate_course(row)

                    # NEW: Enrich course with comprehensive metadata
                    enriched = CourseEnricher.enrich_course(row)
                    self._enriched_courses[enriched.course_id] = enriched

                    # Store enriched metadata in course dict for easy access
                    row["_enriched"] = enriched

                    courses.append(row)
            self._courses = courses

            logger.info(
                "courses_loaded_and_enriched",
                total_courses=len(courses),
                enriched_count=len(self._enriched_courses),
            )
        except FileNotFoundError:
            logger.warning("courses_file_not_found", path=str(COURSES_CSV_PATH))
            self._courses = []

        return self._courses

    def _annotate_course(self, course: dict) -> None:
        """Annotate course with computed features for CBF matching.

        Uses all available data fields:
        - course_title: Primary text for keyword matching
        - subject: Category classification
        - level: Difficulty level (Beginner/Intermediate/Expert/All Levels)
        - content_duration: Course length in hours
        - num_lectures: Number of lecture videos
        - num_subscribers: Popularity metric
        - num_reviews: Quality/engagement metric
        - price: Free vs paid
        - published_timestamp: Course freshness
        """
        title = course.get("course_title", "")
        subject = course.get("subject", "")
        level = course.get("level", "")

        # Combine title + subject + level for richer text representation
        text = f"{title} {subject} {level}".lower()

        # Extract topic tags from text
        tags = self._extract_topic_tags(text)

        # Tokenize for embedding
        tokens = self._tokenize(text)

        # Store computed features
        course["_tags"] = tags
        course["_vector"] = self._hash_embedding(tokens)
        course["_text"] = text  # Store combined text for matching

        # Pre-compute numeric features for scoring
        course["_quality_score"] = self._compute_quality_score(course)
        course["_freshness_score"] = self._compute_freshness_score(course)
        course["_depth_score"] = self._compute_depth_score(course)

    def _compute_quality_score(self, course: dict) -> float:
        """Compute quality score from reviews and subscribers.

        Combines:
        - num_reviews: Direct engagement metric
        - num_subscribers: Popularity metric
        - Review-to-subscriber ratio: Quality indicator
        """
        try:
            subscribers = int(course.get("num_subscribers", 0) or 0)
            reviews = int(course.get("num_reviews", 0) or 0)

            # Popularity component (normalized to 0-0.4)
            popularity = min(0.4, subscribers / 50000)

            # Review count component (normalized to 0-0.3)
            review_score = min(0.3, reviews / 2000)

            # Review-to-subscriber ratio (indicates engagement quality)
            # Higher ratio = more engaged students
            if subscribers > 0:
                engagement_ratio = reviews / subscribers
                engagement_score = min(0.3, engagement_ratio * 3)
            else:
                engagement_score = 0

            return popularity + review_score + engagement_score
        except (ValueError, TypeError):
            return 0.0

    def _compute_freshness_score(self, course: dict) -> float:
        """Compute freshness score from published timestamp.

        Newer courses get higher scores (tech content gets outdated).
        """
        try:
            from datetime import UTC, datetime

            timestamp_str = course.get("published_timestamp", "")
            if not timestamp_str:
                return 0.0

            # Parse ISO format: 2017-01-18T20:58:58Z
            published = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(UTC)

            # Calculate age in years
            age_days = (now - published).days
            age_years = age_days / 365

            # Score: newer = higher, max 0.2
            # Courses < 1 year: 0.2
            # Courses 1-3 years: 0.15
            # Courses 3-5 years: 0.1
            # Courses > 5 years: 0.05
            if age_years < 1:
                return 0.2
            elif age_years < 3:
                return 0.15
            elif age_years < 5:
                return 0.1
            else:
                return 0.05
        except Exception:
            return 0.1  # Default middle score

    def _compute_depth_score(self, course: dict) -> float:
        """Compute depth score from content_duration and num_lectures.

        Indicates how comprehensive the course is.
        """
        try:
            duration = float(course.get("content_duration", 0) or 0)
            lectures = int(course.get("num_lectures", 0) or 0)

            # Duration component (normalized to 0-0.15)
            # Longer courses = more comprehensive
            duration_score = min(0.15, duration / 50)

            # Lecture count component (normalized to 0-0.1)
            lecture_score = min(0.1, lectures / 200)

            # Average lecture length indicator
            # Good courses have balanced lecture lengths (5-15 min each)
            if lectures > 0 and duration > 0:
                avg_lecture_mins = (duration * 60) / lectures
                if 5 <= avg_lecture_mins <= 15:
                    balance_score = 0.05  # Well-structured
                else:
                    balance_score = 0.02
            else:
                balance_score = 0

            return duration_score + lecture_score + balance_score
        except (ValueError, TypeError):
            return 0.0

    def _tokenize(self, text: str) -> list[str]:
        clean = re.sub(r"[^a-z0-9]+", " ", text.lower())
        return [t for t in clean.split() if len(t) > 2 and t not in STOPWORDS]

    def _extract_topic_tags(self, text: str) -> list[str]:
        """Extract topic tags using whole-word matching."""
        tags = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            # Use whole-word matching to avoid false positives
            # e.g., 'api' should not match 'Instagram'
            if any(self._word_match(keyword, text) for keyword in keywords):
                tags.append(topic)
        return tags

    def _hash_embedding(self, tokens: list[str], dim: int = 128) -> list[float]:
        vec = [0.0] * dim
        for token in tokens:
            idx = hash(token) % dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        return sum(x * y for x, y in zip(a, b, strict=False))

    def _parse_tech_preferences(self, tech_prefs: object | None) -> list[str]:
        if not tech_prefs:
            return []

        if isinstance(tech_prefs, list):
            items = [str(item).strip() for item in tech_prefs if str(item).strip()]
        else:
            text = str(tech_prefs).strip()
            if not text:
                return []

            if text.startswith("[") and text.endswith("]"):
                try:
                    parsed = ast.literal_eval(text)
                except (ValueError, SyntaxError):
                    parsed = text
                if isinstance(parsed, list):
                    items = [str(item).strip() for item in parsed if str(item).strip()]
                else:
                    items = [str(parsed).strip()]
            else:
                normalized = text.replace("\n", ",")
                for sep in [";", "|", "/"]:
                    normalized = normalized.replace(sep, ",")
                if "," in normalized:
                    items = [t.strip() for t in normalized.split(",") if t.strip()]
                elif " and " in normalized:
                    items = [t.strip() for t in normalized.split(" and ") if t.strip()]
                elif " & " in normalized:
                    items = [t.strip() for t in normalized.split(" & ") if t.strip()]
                else:
                    items = [normalized]

        return [item.lower() for item in items if item]

    def _has_advanced_learning_target(self, tech_keywords: list[str]) -> bool:
        """Detect whether user target includes advanced technology domains."""
        if not tech_keywords:
            return False

        combined = " ".join(tech_keywords).lower()
        return any(keyword in combined for keyword in ADVANCED_TECH_KEYWORDS)

    def _keyword_in_text(self, keyword: str, text: str) -> bool:
        """Keyword matching that supports both phrase and symbol-based terms."""
        lowered_text = text.lower()
        lowered_keyword = keyword.lower()
        if self._word_match(lowered_keyword, lowered_text):
            return True
        return lowered_keyword in lowered_text

    def _expand_target_keywords_for_matching(self, target_keywords: list[str]) -> list[str]:
        """Expand raw target keywords into catalog-compatible matching terms."""
        expanded: list[str] = []
        seen: set[str] = set()

        for raw_keyword in target_keywords:
            keyword = str(raw_keyword).strip().lower()
            if not keyword:
                continue

            if keyword not in seen:
                expanded.append(keyword)
                seen.add(keyword)

            normalized_keyword = CourseEnricher.normalize_term(keyword)
            mapped_tag: str | None = None
            for tech_tag, aliases in TECH_KEYWORD_MAP.items():
                normalized_tag = CourseEnricher.normalize_term(str(tech_tag))
                if normalized_keyword == normalized_tag:
                    mapped_tag = str(tech_tag).strip().lower()
                    break

                if any(
                    normalized_keyword == CourseEnricher.normalize_term(str(alias))
                    for alias in aliases
                ):
                    mapped_tag = str(tech_tag).strip().lower()
                    break

            if mapped_tag and mapped_tag not in seen:
                expanded.append(mapped_tag)
                seen.add(mapped_tag)

        return expanded

    def _filter_matches_by_target_keywords(
        self,
        matches: list[CourseMatch],
        target_keywords: list[str],
    ) -> list[CourseMatch]:
        """Keep only matches that overlap with target technologies."""
        expanded_keywords = self._expand_target_keywords_for_matching(target_keywords)
        if not expanded_keywords:
            return matches

        filtered: list[CourseMatch] = []
        for match in matches:
            metadata = match.metadata or {}
            raw_tags = metadata.get("tech_tags")
            if raw_tags is None:
                raw_tags = metadata.get("enriched_tags")
            if isinstance(raw_tags, list | tuple | set):
                tags = [str(tag).strip().lower() for tag in raw_tags if str(tag).strip()]
            else:
                tags = [str(raw_tags).strip().lower()] if str(raw_tags or "").strip() else []

            normalized_tags = {CourseEnricher.normalize_term(tag) for tag in tags if tag}
            metadata_subject = str(metadata.get("subject", ""))
            metadata_level = str(metadata.get("level", ""))
            tags_text = " ".join(tags)
            searchable_text = (
                f"{match.title} {match.match_reason} "
                f"{metadata_subject} {metadata_level} "
                f"{tags_text}"
            ).lower()

            has_overlap = any(
                self._keyword_in_text(keyword, searchable_text)
                or CourseEnricher.normalize_term(keyword) in normalized_tags
                for keyword in expanded_keywords
            )
            if has_overlap:
                filtered.append(match)

        return filtered

    def _catalog_has_target_keyword_support(
        self, role_slug: str, target_keywords: list[str]
    ) -> bool:
        """Check whether role-scoped catalog has at least one target keyword candidate."""
        expanded_keywords = self._expand_target_keywords_for_matching(target_keywords)
        if not expanded_keywords:
            return False

        for course in self._load_courses():
            subject = str(course.get("subject", ""))
            if not self._is_role_subject_match(role_slug, subject):
                continue

            enriched = course.get("_enriched")
            tech_tags = (
                " ".join(str(tag) for tag in enriched.tech_tags)
                if enriched and isinstance(enriched.tech_tags, list)
                else ""
            )
            course_title = str(course.get("course_title", ""))
            course_level = str(course.get("level", ""))
            text = (f"{course_title} " f"{subject} " f"{course_level} " f"{tech_tags}").lower()
            if any(self._keyword_in_text(keyword, text) for keyword in expanded_keywords):
                return True

        return False

    def _get_target_keyword_fallback_courses(
        self,
        role_slug: str,
        target_keywords: list[str],
        top_k: int = 5,
    ) -> list[CourseMatch]:
        """Fallback retrieval that still enforces overlap with target technologies."""
        courses = self._load_courses()
        if not courses:
            return []

        expanded_keywords = self._expand_target_keywords_for_matching(target_keywords)
        if not expanded_keywords:
            return []

        query = " ".join(expanded_keywords)
        query_terms = [term for term in query.split() if len(term) > 2]
        query_vec = self._hash_embedding(self._tokenize(query))

        broad_matches = self._score_and_filter_courses(
            courses,
            role_slug=role_slug,
            query_terms=query_terms,
            query_vec=query_vec,
            missed_topics=[],
            tech_pref_keywords=expanded_keywords,
            payment_pref="any",
            duration_pref="any",
            top_k=max(top_k * 3, 10),
            difficulty_pref=None,
            min_keyword_score=0.0,
            strict_payment=False,
        )
        return self._filter_matches_by_target_keywords(broad_matches, target_keywords)[:top_k]

    def _compute_target_complexity_adjustment(
        self, tech_keywords: list[str]
    ) -> tuple[float, str, dict[str, int]]:
        """Compute threshold adjustment based on target technology complexity."""
        if not tech_keywords:
            return (
                0.0,
                "unspecified",
                {
                    "advanced": 0,
                    "intermediate": 0,
                    "foundation": 0,
                    "unknown": 0,
                },
            )

        counters = {"advanced": 0, "intermediate": 0, "foundation": 0, "unknown": 0}
        weighted_sum = 0.0

        for tech in tech_keywords:
            text = str(tech).strip().lower()
            if not text:
                continue

            if any(self._keyword_in_text(keyword, text) for keyword in ADVANCED_TECH_KEYWORDS):
                counters["advanced"] += 1
                weighted_sum += 1.0
                continue

            if any(self._keyword_in_text(keyword, text) for keyword in INTERMEDIATE_TECH_KEYWORDS):
                counters["intermediate"] += 1
                weighted_sum += 0.35
                continue

            if any(self._keyword_in_text(keyword, text) for keyword in FOUNDATION_TECH_KEYWORDS):
                counters["foundation"] += 1
                weighted_sum -= 0.45
                continue

            counters["unknown"] += 1

        denominator = max(len([t for t in tech_keywords if str(t).strip()]), 1)
        avg_weight = weighted_sum / denominator
        complexity_adjustment = round(max(-4.0, min(5.0, avg_weight * 5.0)), 1)

        if counters["advanced"] > 0:
            target_complexity = "advanced"
        elif avg_weight <= -0.2:
            target_complexity = "foundation"
        elif counters["intermediate"] > 0 or avg_weight >= 0.2:
            target_complexity = "intermediate"
        else:
            target_complexity = "unspecified"

        return complexity_adjustment, target_complexity, counters

    def _compute_prerequisite_gap_adjustment(
        self,
        *,
        theoretical_pct: float,
        essay_pct: float,
        profile_pct: float,
        has_essay_scores: bool,
    ) -> float:
        """Raise threshold when prerequisite competency is weak."""
        theoretical_gap = max(0.0, 65.0 - theoretical_pct) * 0.08
        essay_gap = (max(0.0, 60.0 - essay_pct) * 0.06) if has_essay_scores else 0.0
        profile_gap = max(0.0, 45.0 - profile_pct) * 0.05
        return round(min(6.0, theoretical_gap + essay_gap + profile_gap), 1)

    def _compute_experience_bonus(self, profile_signals: dict | None) -> float:
        """Lower threshold when user has stronger project execution evidence."""
        signals = profile_signals or {}
        project_count = self._parse_non_negative_int(signals.get("experience-project-count")) or 0

        if project_count >= 8:
            bonus = 5.0
        elif project_count >= 5:
            bonus = 3.5
        elif project_count >= 3:
            bonus = 2.0
        else:
            bonus = 0.0

        raw_contexts = signals.get("experience-project-contexts")
        contexts = self._clean_text_list(raw_contexts)
        context_text = " ".join(contexts).lower()
        if context_text:
            if any(
                token in context_text
                for token in ("production", "client", "real-world", "freelance", "startup")
            ):
                bonus += 1.0
            if any(
                token in context_text for token in ("team", "collaboration", "cross-functional")
            ):
                bonus += 0.5

        return round(min(6.0, bonus), 1)

    def _build_readiness_policy(
        self,
        role_slug: str,
        profile_signals: dict | None,
        score_metrics: dict[str, float | bool],
        advanced_threshold_pct: float | None = None,
    ) -> dict[str, object]:
        """Build readiness policy for gating recommendation difficulty."""
        tech_prefs = self._parse_tech_preferences((profile_signals or {}).get("tech-preferences"))
        has_target_preferences = bool(tech_prefs)
        targeting_advanced = self._has_advanced_learning_target(tech_prefs)

        overall_pct = float(score_metrics.get("overall_pct", 0.0) or 0.0)
        overall_score = float(score_metrics.get("overall_score", 0.0) or 0.0)
        overall_max = float(score_metrics.get("overall_max", 0.0) or 0.0)
        theoretical_pct = float(score_metrics.get("theoretical_pct", 0.0) or 0.0)
        profile_pct = float(score_metrics.get("profile_pct", 0.0) or 0.0)
        essay_pct = float(score_metrics.get("essay_pct", 0.0) or 0.0)
        has_essay_scores = bool(score_metrics.get("has_essay_scores", False))

        base_threshold_pct = (
            float(advanced_threshold_pct)
            if isinstance(advanced_threshold_pct, int | float)
            else 70.0
        )
        base_threshold_pct = max(0.0, min(100.0, base_threshold_pct))

        complexity_adjustment, target_complexity, complexity_counts = (
            self._compute_target_complexity_adjustment(tech_prefs)
        )
        # Make threshold target-driven: easy targets should start from a lower base.
        target_base_adjustment_map = {
            "advanced": 0.0,
            "intermediate": -12.0,
            "foundation": -28.0,
            "unspecified": -6.0,
        }
        target_base_adjustment = (
            target_base_adjustment_map.get(target_complexity, -6.0)
            if has_target_preferences
            else 0.0
        )
        adjusted_base_threshold_pct = max(
            35.0,
            min(85.0, base_threshold_pct + target_base_adjustment),
        )
        prerequisite_gap_adjustment = self._compute_prerequisite_gap_adjustment(
            theoretical_pct=theoretical_pct,
            essay_pct=essay_pct,
            profile_pct=profile_pct,
            has_essay_scores=has_essay_scores,
        )
        experience_bonus = self._compute_experience_bonus(profile_signals)

        # Hybrid threshold: admin baseline + system dynamic adjustments.
        advanced_kkm = max(
            35.0,
            min(
                85.0,
                adjusted_base_threshold_pct
                + complexity_adjustment
                + prerequisite_gap_adjustment
                - experience_bonus,
            ),
        )
        advanced_kkm = round(advanced_kkm, 1)

        # Readiness tier from observed competence, not from user preference.
        if (
            overall_pct < 55
            or theoretical_pct < 60
            or (has_essay_scores and essay_pct < 55)
            or profile_pct < 35
        ):
            readiness_tier = "foundation"
        elif overall_pct < 75 or theoretical_pct < 72 or (has_essay_scores and essay_pct < 65):
            readiness_tier = "intermediate"
        else:
            readiness_tier = "advanced"
        advanced_eligible = (
            overall_pct >= advanced_kkm
            and theoretical_pct >= 65
            and (not has_essay_scores or essay_pct >= 60)
            and profile_pct >= 45
        )

        force_foundation = has_target_preferences and not advanced_eligible
        foundation_priority = force_foundation or (
            not has_target_preferences and readiness_tier == "foundation"
        )
        if force_foundation:
            difficulty_pref = "beginner"
            if targeting_advanced:
                reason = (
                    "Your target technologies are advanced, and your current score is below "
                    "the minimum readiness threshold. Recommendations are focused on "
                    "fundamentals first."
                )
            else:
                reason = (
                    "Your current score is below the minimum readiness threshold for direct "
                    "target-path learning. Recommendations are focused on fundamentals first."
                )
        elif readiness_tier == "foundation":
            difficulty_pref = "beginner"
            reason = "Your core score is not stable yet, so focus on fundamentals first."
        elif readiness_tier == "intermediate":
            difficulty_pref = "intermediate"  # Matcher still allows beginner.
            reason = (
                "Your score supports an intermediate track with continued "
                "foundation strengthening."
            )
        else:
            difficulty_pref = None
            reason = "Your score is strong enough to pursue advanced topics."

        return {
            "role_slug": role_slug,
            "readiness_tier": readiness_tier,
            "difficulty_pref": difficulty_pref,
            "targeting_advanced": targeting_advanced,
            "has_target_preferences": has_target_preferences,
            "advanced_eligible": advanced_eligible,
            "force_foundation": force_foundation,
            "foundation_priority": foundation_priority,
            "advanced_threshold_pct": advanced_kkm,
            "advanced_kkm": advanced_kkm,
            "base_advanced_threshold_pct": round(adjusted_base_threshold_pct, 1),
            "admin_base_advanced_threshold_pct": round(base_threshold_pct, 1),
            "threshold_adjustments": {
                "target_base_adjustment": target_base_adjustment,
                "complexity": complexity_adjustment,
                "prerequisite_gap": prerequisite_gap_adjustment,
                "experience_bonus": experience_bonus,
                "final": advanced_kkm,
            },
            "target_complexity": target_complexity,
            "target_complexity_counts": complexity_counts,
            "overall_score": round(overall_score, 1),
            "overall_max": round(overall_max, 1),
            "overall_pct": round(overall_pct, 1),
            "theoretical_pct": round(theoretical_pct, 1),
            "profile_pct": round(profile_pct, 1),
            "essay_pct": round(essay_pct, 1),
            "has_essay_scores": has_essay_scores,
            "target_keywords": tech_prefs,
            "reason": reason,
        }

    def _get_role_fallback_keywords(self, role_slug: str) -> list[str]:
        """Get role-safe keywords used when user tech preferences are missing/relaxed."""
        foundation = ROLE_FOUNDATION_KEYWORDS.get(role_slug, [])
        role_keywords = ROLE_KEYWORDS.get(role_slug, [])

        # Keep role keywords focused on fundamentals for fallback retrieval.
        role_safe = [kw for kw in role_keywords if kw.lower() not in ADVANCED_TECH_KEYWORDS]

        merged: list[str] = []
        seen: set[str] = set()
        for keyword in [*foundation, *role_safe]:
            normalized = keyword.strip().lower()
            if not normalized or normalized in seen:
                continue
            merged.append(keyword)
            seen.add(normalized)
        return merged[:10]

    def _is_role_subject_match(self, role_slug: str, subject: str) -> bool:
        """Validate course subject is within role scope."""
        allowed = ROLE_SUBJECTS.get(role_slug)
        if not allowed:
            return True
        subject_clean = (subject or "").strip().lower()
        return any(subject_clean == option.lower() for option in allowed)

    def _build_query(
        self,
        role_slug: str,
        profile_signals: dict | None = None,
        essay_keywords: list[str] | None = None,
        missed_topics: list[str] | None = None,
        foundation_first: bool = False,
    ) -> str:
        """Build RAG query from role context and signals.

        Priority order (highest first):
        1. User's tech preferences (what they explicitly want to learn)
        2. Missed topics from assessment (areas needing improvement)
        3. Essay keywords (topics user discussed)
        4. Role keywords (general role-related terms)
        """
        query_parts = []

        if foundation_first:
            foundation_keywords = ROLE_FOUNDATION_KEYWORDS.get(role_slug) or ROLE_KEYWORDS.get(
                role_slug, []
            )
            if foundation_keywords:
                query_parts.extend(foundation_keywords[:6])
                query_parts.extend(foundation_keywords[:3])  # Boost foundation topics

        # PRIORITY 1: User tech preferences first (most important)
        # User explicitly stated what they want to learn
        if profile_signals:
            tech_prefs = profile_signals.get("tech-preferences")
            pref_keywords = self._parse_tech_preferences(tech_prefs)
            if pref_keywords:
                if foundation_first:
                    # Keep user intent, but avoid over-dominating fundamental path.
                    query_parts.extend(pref_keywords[:3])
                else:
                    # Add tech preferences multiple times for higher weight.
                    query_parts.extend(pref_keywords[:5])
                    query_parts.extend(pref_keywords[:3])  # Repeat for boost

        # PRIORITY 2: Missed topics (areas user needs to improve)
        if missed_topics:
            query_parts.extend(missed_topics[:5])

        # PRIORITY 3: Essay keywords
        if essay_keywords:
            query_parts.extend(essay_keywords[:3])

        # PRIORITY 4: Role keywords (general context, lower priority)
        role_keywords = ROLE_KEYWORDS.get(role_slug, [])
        if role_keywords:
            # Only add role keywords if no strong user preference
            if not profile_signals or not profile_signals.get("tech-preferences"):
                query_parts.extend(role_keywords[:5])
            else:
                # Add fewer role keywords when user has preferences
                query_parts.extend(role_keywords[:2])

        return " ".join(query_parts)

    def _word_match(self, term: str, text: str) -> bool:
        """Check if term matches as whole word in text (not substring).

        Examples:
        - 'rest' in 'REST API' -> True
        - 'rest' in 'Pinterest' -> False
        - 'ruby' in 'Ruby on Rails' -> True
        """
        import re

        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        return bool(re.search(pattern, text.lower()))

    def _calculate_relevance(self, course: dict, query_terms: list[str]) -> float:
        """Calculate relevance score using all available course data.

        Combines:
        - Keyword matching (title + subject + level)
        - Pre-computed quality score (subscribers + reviews + engagement)
        - Pre-computed freshness score (publication date)
        - Pre-computed depth score (duration + lectures)
        """
        # Use pre-computed combined text for matching
        text = course.get("_text", "")
        if not text:
            title = course.get("course_title", "").lower()
            subject = course.get("subject", "").lower()
            text = f"{title} {subject}"

        # Count keyword matches (whole-word)
        matches = 0
        for term in query_terms:
            if self._word_match(term, text):
                matches += 1

        if not query_terms:
            return 0.0

        # Base score from keyword matches (40% weight)
        keyword_score = (matches / len(query_terms)) * 0.4

        # Use pre-computed feature scores
        quality_score = course.get("_quality_score", 0) * 0.3  # 30% weight
        freshness_score = course.get("_freshness_score", 0) * 0.15  # 15% weight
        depth_score = course.get("_depth_score", 0) * 0.15  # 15% weight

        # Fallback to legacy calculation if pre-computed not available
        if quality_score == 0:
            try:
                subscribers = int(course.get("num_subscribers", 0))
                reviews = int(course.get("num_reviews", 0))
                quality_score = min(0.3, (subscribers / 100000 + reviews / 5000) * 0.15)
            except (ValueError, TypeError):
                quality_score = 0

        return min(1.0, keyword_score + quality_score + freshness_score + depth_score)

    def _retrieve_courses(
        self,
        query: str,
        role_slug: str,
        top_k: int = 5,
        missed_topics: list[str] | None = None,
        profile_signals: dict | None = None,
        readiness_policy: dict[str, object] | None = None,
    ) -> list[CourseMatch]:
        """Retrieve top-K courses matching the query.

        Strategy:
        1. First try with all filters (payment preference, etc.)
        2. If not enough results, relax payment filter but keep relevance requirement
        3. Only return courses that match tech preferences OR role keywords
        4. Apply readiness/KKM difficulty gate to avoid over-shoot recommendations
        """
        courses = self._load_courses()
        if not courses:
            return []

        query_terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
        if not query_terms:
            return []

        query_vec = self._hash_embedding(self._tokenize(query))
        missed_topics = missed_topics or []
        profile_signals = profile_signals or {}

        # Extract preferences from profile
        payment_pref = profile_signals.get("payment-preference", "any")
        if isinstance(payment_pref, list):
            payment_pref = payment_pref[0] if payment_pref else "any"
        payment_pref = str(payment_pref).lower()

        duration_pref = profile_signals.get("content-duration", "any")
        if isinstance(duration_pref, list):
            duration_pref = duration_pref[0] if duration_pref else "any"
        duration_pref = str(duration_pref).lower()

        difficulty_pref = (
            str(readiness_policy.get("difficulty_pref"))
            if readiness_policy and readiness_policy.get("difficulty_pref")
            else None
        )
        readiness_reason = (
            str(readiness_policy.get("reason"))
            if readiness_policy and readiness_policy.get("reason")
            else None
        )

        # Parse tech preferences into keywords for exact matching.
        raw_tech_pref_keywords = self._parse_tech_preferences(
            profile_signals.get("tech-preferences")
        )
        if raw_tech_pref_keywords:
            tech_pref_keywords = raw_tech_pref_keywords
            min_keyword_score = 0.0
        else:
            # Guardrail: avoid broad/generic matches by using role-scoped fallback terms.
            tech_pref_keywords = self._get_role_fallback_keywords(role_slug)
            min_keyword_score = 0.05

        def _merge_unique(base: list[CourseMatch], extra: list[CourseMatch]) -> list[CourseMatch]:
            if not extra:
                return base
            merged = list(base)
            seen = {item.course_id for item in merged}
            for candidate in extra:
                if candidate.course_id in seen:
                    continue
                merged.append(candidate)
                seen.add(candidate.course_id)
                if len(merged) >= top_k:
                    break
            return merged

        # First pass: with payment filter
        matches = self._score_and_filter_courses(
            courses,
            role_slug,
            query_terms,
            query_vec,
            missed_topics,
            tech_pref_keywords,
            payment_pref,
            duration_pref,
            top_k,
            difficulty_pref=difficulty_pref,
            readiness_note=readiness_reason,
            min_keyword_score=min_keyword_score,
            strict_payment=True,
        )

        # If not enough relevant results, try without strict payment filter
        if len(matches) < top_k and payment_pref != "any":
            relaxed_payment_matches = self._score_and_filter_courses(
                courses,
                role_slug,
                query_terms,
                query_vec,
                missed_topics,
                tech_pref_keywords,
                payment_pref,
                duration_pref,
                top_k,
                difficulty_pref=difficulty_pref,
                readiness_note=readiness_reason,
                min_keyword_score=min_keyword_score,
                strict_payment=False,
            )
            matches = _merge_unique(matches, relaxed_payment_matches)

        # If forced to foundation and still sparse, relax tech-match to avoid empty output.
        if (
            len(matches) < top_k
            and readiness_policy
            and bool(readiness_policy.get("force_foundation"))
        ):
            foundation_fill = self._score_and_filter_courses(
                courses,
                role_slug,
                query_terms,
                query_vec,
                missed_topics,
                self._get_role_fallback_keywords(role_slug),
                "any",
                duration_pref,
                top_k,
                difficulty_pref="beginner",
                readiness_note=readiness_reason,
                min_keyword_score=0.05,
                strict_payment=False,
            )
            matches = _merge_unique(matches, foundation_fill)

        return matches

    def _score_and_filter_courses(
        self,
        courses: list[dict],
        role_slug: str,
        query_terms: list[str],
        query_vec: list[float],
        missed_topics: list[str],
        tech_pref_keywords: list[str],
        payment_pref: str,
        duration_pref: str,
        top_k: int,
        difficulty_pref: str | None = None,
        readiness_note: str | None = None,
        min_keyword_score: float = 0.0,
        strict_payment: bool = True,
    ) -> list[CourseMatch]:
        """Score and filter courses using enriched metadata for better matching."""
        scored_courses = []

        for course in courses:
            # Get enriched metadata
            enriched = course.get("_enriched")
            if not enriched:
                # Fallback to legacy method if enrichment failed
                continue

            if not self._is_role_subject_match(role_slug, enriched.subject):
                continue

            # Use enriched metadata for precise filtering
            matches, match_score = CourseEnricher.match_user_preferences(
                enriched_course=enriched,
                user_tech_prefs=tech_pref_keywords,
                payment_pref=payment_pref if strict_payment else "any",
                duration_pref=duration_pref,
                difficulty_pref=difficulty_pref,
            )

            if not matches:
                continue  # Course doesn't match user preferences

            # Legacy scoring for backward compatibility
            keyword_score = self._calculate_relevance(course, query_terms)
            embedding_score = self._cosine_similarity(query_vec, course.get("_vector", []))

            # Guardrail for low-signal fallback paths to prevent irrelevant recommendations.
            if keyword_score < min_keyword_score:
                continue

            # Boost for missed topics
            tag_boost = 0.0
            if missed_topics and any(tag in enriched.tech_tags for tag in missed_topics):
                tag_boost = 0.15

            # Build match reason
            reason_parts = []
            if enriched.tech_tags:
                pref_normalized = {CourseEnricher.normalize_term(tag) for tag in tech_pref_keywords}
                matched_tags = [
                    tag
                    for tag in enriched.tech_tags
                    if CourseEnricher.normalize_term(tag) in pref_normalized
                ]
                if matched_tags:
                    matched_display = ", ".join(matched_tags[:3])
                    reason_parts.append(f"Matches your interest in: {matched_display}")
                else:
                    covered_display = ", ".join(enriched.tech_tags[:3])
                    reason_parts.append(f"Covers: {covered_display}")

            if readiness_note:
                reason_parts.append("Readiness gate applied")

            if enriched.difficulty:
                reason_parts.append(f"{enriched.difficulty.capitalize()} level")

            if enriched.is_free:
                reason_parts.append("Free course")

            reason_parts.append(f"{enriched.duration_hours:.1f}h duration")

            if enriched.num_subscribers > 10000:
                reason_parts.append(f"{enriched.num_subscribers:,} students")

            match_reason = " • ".join(reason_parts)

            # Combine all scores
            # Priority: enriched match score > keyword/embedding > quality
            final_score = (
                match_score * 0.5  # 50% from enriched metadata matching
                + keyword_score * 0.2  # 20% from keyword relevance
                + embedding_score * 0.1  # 10% from embedding similarity
                + tag_boost  # Boost for missed topics
                + enriched.quality_score * 0.2  # 20% from quality
            )

            scored_courses.append((final_score, course, match_reason))

        # Sort by score descending
        scored_courses.sort(key=lambda x: x[0], reverse=True)

        # Return top K
        return [
            CourseMatch(
                course_id=course.get("course_id", ""),
                title=course.get("course_title", ""),
                url=course.get("url"),
                relevance_score=round(score, 3),
                match_reason=reason,
                metadata={
                    "subject": course.get("subject", ""),
                    "level": course.get("level", ""),
                    "duration_hours": float(course.get("content_duration", 0) or 0),
                    "is_paid": str(course.get("is_paid", "False")).lower() in {"true", "1", "yes"},
                    "price": float(course.get("price", 0) or 0),
                    "subscribers": int(course.get("num_subscribers", 0) or 0),
                    "num_reviews": int(course.get("num_reviews", 0) or 0),
                    "enriched_tags": (
                        list(course.get("_enriched").tech_tags) if course.get("_enriched") else []
                    ),
                    "tech_tags": (
                        list(course.get("_enriched").tech_tags) if course.get("_enriched") else []
                    ),
                },
            )
            for score, course, reason in scored_courses[:top_k]
        ]

    async def retrieve_recommendations(
        self,
        assessment_id: str,
        role_slug: str,
        profile_signals: dict | None = None,
        essay_keywords: list[str] | None = None,
        missed_topics: list[str] | None = None,
        top_k: int = 5,
        readiness_policy: dict[str, object] | None = None,
        enable_fallback: bool = True,
    ) -> RAGResult:
        """
        Retrieve role-aware recommendations for an assessment.

        AC1: Composes RAG query from track tags, profile signals, and essay embeddings.
        AC2: Returns Top-K credentials with metadata.
        AC4: Static fallback when retrieval fails.
        """
        query = self._build_query(
            role_slug,
            profile_signals,
            essay_keywords,
            missed_topics,
            foundation_first=bool(
                readiness_policy
                and (
                    readiness_policy.get("force_foundation")
                    or readiness_policy.get("foundation_priority")
                )
            ),
        )

        try:
            matches = self._retrieve_courses(
                query,
                role_slug,
                top_k,
                missed_topics,
                profile_signals,
                readiness_policy=readiness_policy,
            )

            if not matches:
                if not enable_fallback:
                    await logger.ainfo(
                        "rag_no_matches",
                        assessment_id=assessment_id,
                        query=query,
                    )
                    return RAGResult(
                        query=query,
                        matches=[],
                        readiness=readiness_policy,
                    )

                # AC4: Static fallback
                await logger.ainfo(
                    "rag_fallback_activated",
                    assessment_id=assessment_id,
                    reason="no_matches",
                )
                return RAGResult(
                    query=query,
                    matches=self._get_fallback_courses(role_slug, top_k),
                    degraded=True,
                    readiness=readiness_policy,
                )

            await logger.ainfo(
                "rag_retrieval_success",
                assessment_id=assessment_id,
                query=query,
                match_count=len(matches),
                readiness_tier=(
                    readiness_policy.get("readiness_tier") if readiness_policy else None
                ),
                forced_foundation=(
                    readiness_policy.get("force_foundation") if readiness_policy else False
                ),
            )

            return RAGResult(query=query, matches=matches, readiness=readiness_policy)

        except Exception as e:
            await logger.aerror(
                "rag_retrieval_failed",
                assessment_id=assessment_id,
                error=str(e),
            )
            if not enable_fallback:
                return RAGResult(
                    query=query,
                    matches=[],
                    error=str(e),
                    readiness=readiness_policy,
                )
            # AC4: Static fallback on error
            return RAGResult(
                query=query,
                matches=self._get_fallback_courses(role_slug, top_k),
                degraded=True,
                error=str(e),
                readiness=readiness_policy,
            )

    def _get_fallback_courses(self, role_slug: str, top_k: int = 5) -> list[CourseMatch]:
        """Get static fallback courses when RAG fails."""
        courses = self._load_courses()
        if not courses:
            return []

        role_keywords = self._get_role_fallback_keywords(role_slug)
        candidates: list[tuple[float, list[str], dict]] = []

        for course in courses:
            subject = str(course.get("subject", ""))
            if not self._is_role_subject_match(role_slug, subject):
                continue

            enriched = course.get("_enriched")
            tech_tags = (
                [str(tag).strip().lower() for tag in enriched.tech_tags]
                if enriched and isinstance(enriched.tech_tags, list)
                else []
            )
            course_title = str(course.get("course_title", ""))
            course_level = str(course.get("level", ""))
            tags_text = " ".join(tech_tags)
            searchable_text = (
                f"{course_title} " f"{subject} " f"{course_level} " f"{tags_text}"
            ).lower()

            matched_keywords = [
                keyword
                for keyword in role_keywords
                if self._keyword_in_text(keyword, searchable_text)
            ]
            if role_keywords and not matched_keywords:
                continue

            keyword_ratio = len(matched_keywords) / max(len(role_keywords), 1)
            quality_score = (
                float(enriched.quality_score)
                if enriched and enriched.quality_score is not None
                else 0.0
            )
            popularity_score = (
                float(enriched.popularity_score)
                if enriched and enriched.popularity_score is not None
                else min(1.0, int(course.get("num_subscribers", 0) or 0) / 100000)
            )
            score = (keyword_ratio * 0.65) + (quality_score * 0.25) + (popularity_score * 0.10)
            candidates.append((score, matched_keywords, course))

        if not candidates:
            return []

        candidates.sort(key=lambda item: item[0], reverse=True)

        matches: list[CourseMatch] = []
        for score, matched_keywords, course in candidates[:top_k]:
            num_reviews = int(course.get("num_reviews", "0") or 0)
            num_subscribers = int(course.get("num_subscribers", "0") or 0)
            level = str(course.get("level", "")).lower()
            enriched = course.get("_enriched")
            tags = (
                list(enriched.tech_tags)
                if enriched and isinstance(enriched.tech_tags, list)
                else []
            )

            reason_parts = ["Role-aligned fallback recommendation"]
            if matched_keywords:
                reason_parts.append("Covers: " + ", ".join(matched_keywords[:3]))
            if num_subscribers > 10000:
                reason_parts.append(f"{num_subscribers:,} students")
            if num_reviews > 100:
                reason_parts.append(f"{num_reviews} reviews")
            if "beginner" in level or "all levels" in level:
                reason_parts.append("Beginner-friendly")
            match_reason = " • ".join(reason_parts)

            matches.append(
                CourseMatch(
                    course_id=course.get("course_id", ""),
                    title=course.get("course_title", ""),
                    url=course.get("url"),
                    relevance_score=round(min(0.75, max(0.4, score)), 3),
                    match_reason=match_reason,
                    metadata={
                        "subject": course.get("subject", ""),
                        "level": course.get("level", ""),
                        "is_paid": str(course.get("is_paid", "False")).lower()
                        in {"true", "1", "yes"},
                        "num_subscribers": num_subscribers,
                        "num_reviews": num_reviews,
                        "tech_tags": tags,
                        "enriched_tags": tags,
                    },
                )
            )

        return matches

    def _tag_matches_with_learning_path(
        self,
        matches: list[CourseMatch],
        path_key: str,
        path_label: str,
    ) -> list[CourseMatch]:
        """Attach learning-path metadata to recommendation matches."""
        tagged: list[CourseMatch] = []
        for match in matches:
            metadata = dict(match.metadata or {})
            metadata["learning_path"] = path_key
            metadata["learning_path_label"] = path_label

            base_reason = (match.match_reason or "").strip()
            if base_reason:
                tagged_reason = f"{path_label} • {base_reason}"
            else:
                tagged_reason = path_label

            tagged.append(
                CourseMatch(
                    course_id=match.course_id,
                    title=match.title,
                    url=match.url,
                    relevance_score=match.relevance_score,
                    match_reason=tagged_reason,
                    metadata=metadata,
                )
            )
        return tagged

    def _merge_unique_matches(
        self,
        primary: list[CourseMatch],
        secondary: list[CourseMatch],
        limit: int,
    ) -> list[CourseMatch]:
        """Merge two ranked lists while preserving order and removing duplicates."""
        merged: list[CourseMatch] = []
        seen_ids: set[str] = set()
        for source in (primary, secondary):
            for item in source:
                if item.course_id in seen_ids:
                    continue
                merged.append(item)
                seen_ids.add(item.course_id)
                if len(merged) >= limit:
                    return merged
        return merged

    @staticmethod
    def _append_learning_path_note(learning_paths: dict[str, object], note: str | None) -> None:
        """Append note text without losing existing context."""
        if not isinstance(note, str):
            return
        cleaned_note = note.strip()
        if not cleaned_note:
            return

        existing = str(learning_paths.get("note") or "").strip()
        learning_paths["note"] = f"{existing} {cleaned_note}".strip() if existing else cleaned_note

    def _compute_target_coverage_context(
        self,
        target_keywords: list[str],
        target_matches: list[CourseMatch],
    ) -> dict[str, object]:
        """Compute how well target technologies are covered by catalog and recommendations."""
        normalized_keywords: list[str] = []
        seen_keywords: set[str] = set()
        for raw_keyword in target_keywords:
            keyword = str(raw_keyword).strip().lower()
            if not keyword or keyword in seen_keywords:
                continue
            seen_keywords.add(keyword)
            normalized_keywords.append(keyword)

        if not normalized_keywords:
            return {
                "target_keywords": [],
                "covered_keywords": [],
                "missing_keywords": [],
                "catalog_covered_keywords": [],
                "catalog_missing_keywords": [],
                "covered_count": 0,
                "target_count": 0,
                "coverage_percentage": 0.0,
                "coverage_ratio": 0.0,
                "catalog_coverage_ratio": 0.0,
                "note": "",
            }

        courses = self._load_courses()
        catalog_texts: list[str] = []
        for course in courses:
            enriched = course.get("_enriched")
            tech_tags = (
                " ".join(str(tag) for tag in enriched.tech_tags)
                if enriched and isinstance(enriched.tech_tags, list)
                else ""
            )
            title = str(course.get("course_title", ""))
            subject = str(course.get("subject", ""))
            level = str(course.get("level", ""))
            catalog_texts.append((f"{title} " f"{subject} " f"{level} " f"{tech_tags}").lower())

        catalog_covered = [
            keyword
            for keyword in normalized_keywords
            if any(self._keyword_in_text(keyword, text) for text in catalog_texts)
        ]
        catalog_missing = [
            keyword for keyword in normalized_keywords if keyword not in catalog_covered
        ]

        recommendation_texts: list[str] = []
        for match in target_matches:
            metadata = match.metadata or {}
            tech_tags = metadata.get("tech_tags")
            if tech_tags is None:
                tech_tags = metadata.get("enriched_tags")
            if isinstance(tech_tags, list | tuple | set):
                tags_text = " ".join(str(tag) for tag in tech_tags)
            else:
                tags_text = str(tech_tags or "")
            reason = str(match.match_reason or "")
            subject = str(metadata.get("subject", ""))
            level = str(metadata.get("level", ""))

            recommendation_texts.append(
                (f"{match.title} " f"{reason} " f"{subject} " f"{level} " f"{tags_text}").lower()
            )

        covered_in_recommendations = [
            keyword
            for keyword in normalized_keywords
            if any(self._keyword_in_text(keyword, text) for text in recommendation_texts)
        ]
        missing_in_recommendations = [
            keyword for keyword in normalized_keywords if keyword not in covered_in_recommendations
        ]

        total_keywords = len(normalized_keywords)
        covered_count = len(covered_in_recommendations)
        coverage_ratio = round(covered_count / total_keywords, 2)
        catalog_coverage_ratio = round(len(catalog_covered) / total_keywords, 2)
        coverage_percentage = round(coverage_ratio * 100.0, 1)

        notes: list[str] = []
        if catalog_missing:
            notes.append(
                "Some target technologies are not available in the current course catalog: "
                + ", ".join(catalog_missing)
                + "."
            )
        remaining_missing = [
            keyword for keyword in missing_in_recommendations if keyword not in catalog_missing
        ]
        if remaining_missing:
            notes.append(
                "Some available targets were not matched in the top recommendations: "
                + ", ".join(remaining_missing)
                + "."
            )

        return {
            "target_keywords": normalized_keywords,
            "covered_keywords": covered_in_recommendations,
            "missing_keywords": missing_in_recommendations,
            "catalog_covered_keywords": catalog_covered,
            "catalog_missing_keywords": catalog_missing,
            "covered_count": covered_count,
            "target_count": total_keywords,
            "coverage_percentage": coverage_percentage,
            "coverage_ratio": coverage_ratio,
            "catalog_coverage_ratio": catalog_coverage_ratio,
            "note": " ".join(notes).strip(),
        }

    async def _retrieve_with_learning_paths(
        self,
        assessment_id: str,
        role_slug: str,
        profile_signals: dict | None,
        essay_keywords: list[str] | None,
        missed_topics: list[str] | None,
        readiness_policy: dict[str, object],
    ) -> RAGResult:
        """
        Build recommendations with two-path output when advanced target isn't ready.

        Path model:
        - Mandatory Foundation: required courses for current readiness.
        - Target Path (Aspirational): user-desired stack as next phase.
        """
        force_foundation = bool(readiness_policy.get("force_foundation"))
        has_target_preferences = bool(readiness_policy.get("has_target_preferences"))
        foundation_priority = bool(readiness_policy.get("foundation_priority"))
        readiness_tier = str(readiness_policy.get("readiness_tier") or "").strip().lower()
        target_keywords = self._parse_tech_preferences(
            (profile_signals or {}).get("tech-preferences")
        )
        catalog_has_target_support = (
            self._catalog_has_target_keyword_support(role_slug, target_keywords)
            if has_target_preferences
            else False
        )
        enforce_target_overlap = (
            has_target_preferences
            and readiness_tier in {"intermediate", "advanced"}
            and catalog_has_target_support
        )

        # Foundation-first mode without explicit target preference.
        # Keep output as two-path envelope so FE can render mandatory section consistently.
        if foundation_priority and not has_target_preferences:
            foundation_profile_signals = dict(profile_signals or {})
            foundation_profile_signals.pop("tech-preferences", None)
            foundation_policy = dict(readiness_policy)
            foundation_policy["force_foundation"] = True
            foundation_result = await self.retrieve_recommendations(
                assessment_id=assessment_id,
                role_slug=role_slug,
                profile_signals=foundation_profile_signals,
                essay_keywords=essay_keywords,
                missed_topics=missed_topics,
                top_k=5,
                readiness_policy=foundation_policy,
            )
            foundation_matches = self._tag_matches_with_learning_path(
                foundation_result.matches[:5],
                path_key="mandatory_foundation",
                path_label="Mandatory Foundation",
            )
            readiness_with_paths = dict(foundation_result.readiness or readiness_policy)
            learning_paths = {
                "mode": "two-path",
                "mandatory_foundation_count": len(foundation_matches),
                "mandatory_bridge_count": 0,
                "mandatory_target_overlap_count": 0,
                "target_path_count": 0,
                "mandatory_foundation_query": foundation_result.query,
                "target_path_query": "",
                "target_path_fallback_used": False,
                "note": (
                    "No explicit target technologies were provided. Recommendations are focused "
                    "on Mandatory Foundation based on your current readiness."
                ),
            }
            readiness_with_paths["learning_paths"] = learning_paths
            readiness_with_paths["target_coverage"] = self._compute_target_coverage_context(
                target_keywords=target_keywords,
                target_matches=[],
            )
            return RAGResult(
                query=foundation_result.query,
                matches=foundation_matches,
                degraded=foundation_result.degraded,
                error=foundation_result.error,
                readiness=readiness_with_paths,
            )

        if not force_foundation:
            base_result = await self.retrieve_recommendations(
                assessment_id=assessment_id,
                role_slug=role_slug,
                profile_signals=profile_signals,
                essay_keywords=essay_keywords,
                missed_topics=missed_topics,
                readiness_policy=readiness_policy,
                enable_fallback=not enforce_target_overlap,
            )
            target_matches = list(base_result.matches)
            target_path_broadened = False

            if enforce_target_overlap:
                target_matches = self._filter_matches_by_target_keywords(
                    target_matches, target_keywords
                )

            if has_target_preferences and len(target_matches) < 5:
                relaxed_profile_signals = dict(profile_signals or {})
                relaxed_profile_signals["content-duration"] = "any"
                relaxed_profile_signals["payment-preference"] = "any"
                relaxed_result = await self.retrieve_recommendations(
                    assessment_id=assessment_id,
                    role_slug=role_slug,
                    profile_signals=relaxed_profile_signals,
                    essay_keywords=essay_keywords,
                    missed_topics=missed_topics,
                    top_k=5,
                    readiness_policy=readiness_policy,
                    enable_fallback=False,
                )
                relaxed_matches = list(relaxed_result.matches)
                if enforce_target_overlap:
                    relaxed_matches = self._filter_matches_by_target_keywords(
                        relaxed_matches, target_keywords
                    )
                merged_matches = self._merge_unique_matches(
                    target_matches, relaxed_matches, limit=5
                )
                target_path_broadened = target_path_broadened or len(merged_matches) > len(
                    target_matches
                )
                target_matches = merged_matches

            if has_target_preferences and len(target_matches) < 5:
                keyword_fallback = self._get_target_keyword_fallback_courses(
                    role_slug=role_slug,
                    target_keywords=target_keywords,
                    top_k=5,
                )
                merged_matches = self._merge_unique_matches(
                    target_matches, keyword_fallback, limit=5
                )
                target_path_broadened = target_path_broadened or len(merged_matches) > len(
                    target_matches
                )
                target_matches = merged_matches

            tagged_matches = self._tag_matches_with_learning_path(
                target_matches[:5],
                path_key="target_path",
                path_label="Target Path",
            )
            readiness_with_paths = dict(base_result.readiness or readiness_policy)
            learning_paths = {
                "mode": "single-path",
                "target_path_count": len(tagged_matches),
                "mandatory_foundation_count": 0,
                "mandatory_bridge_count": 0,
                "mandatory_target_overlap_count": 0,
                "target_path_fallback_used": bool(base_result.degraded or target_path_broadened),
            }
            if base_result.degraded:
                self._append_learning_path_note(
                    learning_paths,
                    "Recommendations were broadened because direct matches were limited.",
                )
            if target_path_broadened:
                self._append_learning_path_note(
                    learning_paths,
                    "Target Path was broadened by relaxing duration/payment filters while "
                    "preserving target-topic relevance.",
                )
            if enforce_target_overlap:
                self._append_learning_path_note(
                    learning_paths,
                    "Target Path enforces overlap with your selected technologies.",
                )
            coverage = self._compute_target_coverage_context(
                target_keywords=target_keywords,
                target_matches=tagged_matches,
            )
            self._append_learning_path_note(learning_paths, str(coverage.get("note") or ""))
            readiness_with_paths["learning_paths"] = learning_paths
            readiness_with_paths["target_coverage"] = coverage
            return RAGResult(
                query=base_result.query,
                matches=tagged_matches,
                degraded=base_result.degraded,
                error=base_result.error,
                readiness=readiness_with_paths,
            )

        # Two-path mode for not-yet-ready advanced targets.
        foundation_profile_signals = dict(profile_signals or {})
        foundation_profile_signals.pop("tech-preferences", None)
        foundation_result = await self.retrieve_recommendations(
            assessment_id=assessment_id,
            role_slug=role_slug,
            profile_signals=foundation_profile_signals,
            essay_keywords=essay_keywords,
            missed_topics=missed_topics,
            top_k=5,
            readiness_policy=readiness_policy,
        )
        foundation_source_matches = list(foundation_result.matches[:5])

        target_policy = dict(readiness_policy)
        target_policy["force_foundation"] = False
        target_policy["difficulty_pref"] = None
        target_policy["reason"] = None
        target_result = await self.retrieve_recommendations(
            assessment_id=assessment_id,
            role_slug=role_slug,
            profile_signals=profile_signals,
            essay_keywords=essay_keywords,
            missed_topics=missed_topics,
            top_k=5,
            readiness_policy=target_policy,
            enable_fallback=False,
        )
        target_source_matches = self._filter_matches_by_target_keywords(
            target_result.matches, target_keywords
        )
        target_candidate_pool = list(target_source_matches)
        target_fallback_used = False
        bridge_filters_relaxed = False

        # Target path can be empty when user duration/payment filters are too strict
        # for advanced topic coverage in current catalog. Relax those filters first,
        # but keep target-keyword overlap to avoid generic recommendations.
        if not target_source_matches:
            relaxed_profile_signals = dict(profile_signals or {})
            relaxed_profile_signals["content-duration"] = "any"
            relaxed_profile_signals["payment-preference"] = "any"
            target_result = await self.retrieve_recommendations(
                assessment_id=assessment_id,
                role_slug=role_slug,
                profile_signals=relaxed_profile_signals,
                essay_keywords=essay_keywords,
                missed_topics=missed_topics,
                top_k=5,
                readiness_policy=target_policy,
                enable_fallback=False,
            )
            relaxed_target_matches = self._filter_matches_by_target_keywords(
                target_result.matches, target_keywords
            )
            target_candidate_pool = self._merge_unique_matches(
                target_candidate_pool,
                relaxed_target_matches,
                limit=50,
            )
            target_source_matches = relaxed_target_matches
            target_fallback_used = bool(target_source_matches)

        if not target_source_matches:
            fallback_target_matches = self._get_target_keyword_fallback_courses(
                role_slug=role_slug,
                target_keywords=target_keywords,
                top_k=5,
            )
            target_candidate_pool = self._merge_unique_matches(
                target_candidate_pool,
                fallback_target_matches,
                limit=50,
            )
            if fallback_target_matches:
                target_source_matches = fallback_target_matches
                target_fallback_used = True

        # Keep richer candidate pool for bridge + de-dup fill.
        if has_target_preferences and len(target_candidate_pool) < 10:
            fallback_pool = self._get_target_keyword_fallback_courses(
                role_slug=role_slug,
                target_keywords=target_keywords,
                top_k=10,
            )
            target_candidate_pool = self._merge_unique_matches(
                target_candidate_pool,
                fallback_pool,
                limit=50,
            )

        def _is_bridge_candidate(match: CourseMatch) -> bool:
            level_text = str((match.metadata or {}).get("level", ""))
            difficulty = CourseEnricher.normalize_difficulty(level_text)
            return difficulty in {"beginner", "intermediate"}

        def _bridge_priority(match: CourseMatch) -> tuple[int, int, float]:
            level_text = str((match.metadata or {}).get("level", ""))
            difficulty = CourseEnricher.normalize_difficulty(level_text)
            diff_rank = {"beginner": 0, "intermediate": 1}.get(difficulty, 2)
            combined_text = f"{match.title} {match.match_reason}".lower()
            intro_tokens = (
                "intro",
                "introduction",
                "fundamental",
                "foundation",
                "basic",
                "beginner",
                "essential",
            )
            intro_rank = 0 if any(token in combined_text for token in intro_tokens) else 1
            return (diff_rank, intro_rank, -float(match.relevance_score))

        foundation_ids = {match.course_id for match in foundation_source_matches}
        target_seed_ids = {match.course_id for match in target_source_matches[:5]}
        bridge_pool_non_seed = [
            match
            for match in target_candidate_pool
            if match.course_id not in foundation_ids
            and match.course_id not in target_seed_ids
            and _is_bridge_candidate(match)
        ]
        bridge_pool_fallback = [
            match
            for match in target_candidate_pool
            if match.course_id not in foundation_ids and _is_bridge_candidate(match)
        ]
        bridge_source = (
            min(bridge_pool_non_seed, key=_bridge_priority)
            if bridge_pool_non_seed
            else (min(bridge_pool_fallback, key=_bridge_priority) if bridge_pool_fallback else None)
        )
        bridge_filters_relaxed = bridge_filters_relaxed or (
            bridge_source is not None and target_fallback_used
        )
        if bridge_source is None and has_target_preferences:
            bridge_policy = dict(target_policy)
            bridge_policy["difficulty_pref"] = "intermediate"
            bridge_result = await self.retrieve_recommendations(
                assessment_id=assessment_id,
                role_slug=role_slug,
                profile_signals=profile_signals,
                essay_keywords=essay_keywords,
                missed_topics=missed_topics,
                top_k=5,
                readiness_policy=bridge_policy,
                enable_fallback=False,
            )
            bridge_candidates = self._filter_matches_by_target_keywords(
                bridge_result.matches, target_keywords
            )
            target_candidate_pool = self._merge_unique_matches(
                target_candidate_pool,
                bridge_candidates,
                limit=50,
            )
            bridge_pool = [
                match
                for match in bridge_candidates
                if match.course_id not in foundation_ids and _is_bridge_candidate(match)
            ]
            bridge_source = min(bridge_pool, key=_bridge_priority) if bridge_pool else None
            if bridge_source is None:
                relaxed_bridge_signals = dict(profile_signals or {})
                relaxed_bridge_signals["content-duration"] = "any"
                relaxed_bridge_signals["payment-preference"] = "any"
                relaxed_bridge_result = await self.retrieve_recommendations(
                    assessment_id=assessment_id,
                    role_slug=role_slug,
                    profile_signals=relaxed_bridge_signals,
                    essay_keywords=essay_keywords,
                    missed_topics=missed_topics,
                    top_k=5,
                    readiness_policy=bridge_policy,
                    enable_fallback=False,
                )
                relaxed_bridge_candidates = self._filter_matches_by_target_keywords(
                    relaxed_bridge_result.matches, target_keywords
                )
                target_candidate_pool = self._merge_unique_matches(
                    target_candidate_pool,
                    relaxed_bridge_candidates,
                    limit=50,
                )
                bridge_pool = [
                    match
                    for match in relaxed_bridge_candidates
                    if match.course_id not in foundation_ids and _is_bridge_candidate(match)
                ]
                bridge_source = min(bridge_pool, key=_bridge_priority) if bridge_pool else None
                bridge_filters_relaxed = bridge_filters_relaxed or bridge_source is not None

        # Keep Target Path intact when no replacement candidate exists.
        if bridge_source is not None and bridge_source.course_id in target_seed_ids:
            replacement_candidates = [
                match
                for match in target_candidate_pool
                if match.course_id not in foundation_ids and match.course_id not in target_seed_ids
            ]
            if not replacement_candidates:
                bridge_source = None
                bridge_filters_relaxed = False

        mandatory_foundation_matches = self._tag_matches_with_learning_path(
            foundation_source_matches[:4] if bridge_source else foundation_source_matches[:5],
            path_key="mandatory_foundation",
            path_label="Mandatory Foundation",
        )

        mandatory_bridge_count = 0
        if bridge_source is not None:
            bridge_reason = (bridge_source.match_reason or "").strip()
            bridge_reason_text = (
                f"Target Bridge • {bridge_reason}" if bridge_reason else "Target Bridge"
            )
            bridge_metadata = dict(bridge_source.metadata or {})
            bridge_metadata["target_bridge"] = True
            bridge_match = CourseMatch(
                course_id=bridge_source.course_id,
                title=bridge_source.title,
                url=bridge_source.url,
                relevance_score=bridge_source.relevance_score,
                match_reason=bridge_reason_text,
                metadata=bridge_metadata,
            )
            tagged_bridge = self._tag_matches_with_learning_path(
                [bridge_match],
                path_key="mandatory_foundation",
                path_label="Mandatory Foundation",
            )
            mandatory_foundation_matches = self._merge_unique_matches(
                mandatory_foundation_matches,
                tagged_bridge,
                limit=5,
            )
            mandatory_bridge_count = len(tagged_bridge)

        mandatory_target_overlap_count = len(
            self._filter_matches_by_target_keywords(mandatory_foundation_matches, target_keywords)
        )

        mandatory_ids = {match.course_id for match in mandatory_foundation_matches[:5]}
        target_unique_source = [
            match for match in target_source_matches if match.course_id not in mandatory_ids
        ]
        for candidate in target_candidate_pool:
            if len(target_unique_source) >= 5:
                break
            if candidate.course_id in mandatory_ids:
                continue
            if any(existing.course_id == candidate.course_id for existing in target_unique_source):
                continue
            target_unique_source.append(candidate)

        target_matches = self._tag_matches_with_learning_path(
            target_unique_source[:5],
            path_key="target_path",
            path_label="Target Path (Aspirational)",
        )

        # Keep both paths independent so users receive top-5 per path.
        combined = [*mandatory_foundation_matches[:5], *target_matches[:5]]
        readiness_with_paths = dict(readiness_policy)
        note = (
            "Target Path is aspirational. Complete Mandatory Foundation first "
            "to reduce learning failure risk."
        )
        if bridge_source is not None:
            note += " Mandatory Foundation includes one Target Bridge course for alignment."
        if bridge_filters_relaxed:
            note += (
                " Mandatory Target Bridge was selected after relaxing duration/payment filters "
                "to avoid sparse results."
            )
        if target_fallback_used:
            note += (
                " Target Path was broadened by relaxing duration/payment filters while "
                "preserving target-topic relevance."
            )
        if has_target_preferences and not target_matches:
            note += (
                " No target-path courses matched your selected technologies in the current catalog."
            )
        coverage = self._compute_target_coverage_context(
            target_keywords=target_keywords,
            target_matches=target_matches[:5],
        )
        learning_paths = {
            "mode": "two-path",
            "mandatory_foundation_count": len(mandatory_foundation_matches[:5]),
            "mandatory_bridge_count": mandatory_bridge_count,
            "mandatory_target_overlap_count": mandatory_target_overlap_count,
            "target_path_count": len(target_matches[:5]),
            "mandatory_foundation_query": foundation_result.query,
            "target_path_query": target_result.query,
            "target_path_fallback_used": target_fallback_used,
            "note": note,
        }
        self._append_learning_path_note(learning_paths, str(coverage.get("note") or ""))
        readiness_with_paths["learning_paths"] = learning_paths
        readiness_with_paths["target_coverage"] = coverage

        return RAGResult(
            query=foundation_result.query,
            matches=combined,
            degraded=foundation_result.degraded,
            error=foundation_result.error or target_result.error,
            readiness=readiness_with_paths,
        )

    async def process_rag_job(self, assessment_id: str) -> RAGResult:
        """
        Process RAG job for an assessment.

        AC3: Results persisted in recommendation_items with ranked order.
        """
        # Get assessment with role
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await self.session.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise RAGRetrievalError(f"Assessment {assessment_id} not found")

        # Get job
        job_stmt = select(AsyncJob).where(
            AsyncJob.assessment_id == assessment_id,
            AsyncJob.job_type == JobType.RAG.value,
        )
        job_result = await self.session.execute(job_stmt)
        job = job_result.scalar_one_or_none()

        if job:
            await self._update_job_progress(
                job,
                status=JobStatus.IN_PROGRESS.value,
                progress_percentage=8.0,
                progress_step="Collecting profile signals",
            )

        try:
            # Extract profile signals from responses
            profile_signals = await self._extract_profile_signals(assessment_id)
            if job:
                await self._update_job_progress(
                    job,
                    progress_percentage=22.0,
                    progress_step="Analyzing profile responses",
                )

            # Extract essay keywords from scores/responses
            essay_keywords = await self._extract_essay_keywords(assessment_id)
            missed_topics = await self._extract_missed_topics(assessment_id)
            score_metrics = await self._extract_score_metrics(assessment_id)
            configured_threshold = await self.session.scalar(
                select(RoleCatalog.advanced_threshold_pct).where(
                    RoleCatalog.slug == assessment.role_slug
                )
            )
            readiness_policy = self._build_readiness_policy(
                assessment.role_slug,
                profile_signals,
                score_metrics,
                advanced_threshold_pct=(
                    float(configured_threshold)
                    if isinstance(configured_threshold, int | float)
                    else None
                ),
            )
            if job:
                await self._update_job_progress(
                    job,
                    progress_percentage=45.0,
                    progress_step="Building retrieval query",
                )

            # Retrieve recommendations with readiness-aware learning paths.
            rag_result = await self._retrieve_with_learning_paths(
                assessment_id=assessment_id,
                role_slug=assessment.role_slug,
                profile_signals=profile_signals,
                essay_keywords=essay_keywords,
                missed_topics=missed_topics,
                readiness_policy=readiness_policy,
            )
            if job:
                await self._update_job_progress(
                    job,
                    progress_percentage=75.0,
                    progress_step="Ranking recommended courses",
                )

            # AC3: Persist results
            await self._persist_recommendation_items(assessment_id, rag_result)

            # Update job status
            if job:
                payload_extra = (
                    {"degraded": True, "reason": rag_result.error or "fallback"}
                    if rag_result.degraded
                    else None
                )
                await self._update_job_progress(
                    job,
                    status=JobStatus.COMPLETED.value,
                    progress_percentage=100.0,
                    progress_step="Completed",
                    payload_extra=payload_extra,
                )
            else:
                await self.session.commit()

            return rag_result
        except Exception as exc:
            if job:
                await self._update_job_progress(
                    job,
                    status=JobStatus.FAILED.value,
                    progress_percentage=95.0,
                    progress_step="Failed",
                    error_payload={"message": str(exc)},
                )
            else:
                await self.session.rollback()
            raise

    async def _update_job_progress(
        self,
        job: AsyncJob,
        *,
        progress_percentage: float,
        progress_step: str | None = None,
        status: str | None = None,
        payload_extra: dict[str, Any] | None = None,
        error_payload: dict[str, Any] | None = None,
    ) -> None:
        """Persist granular job progress for real-time status polling."""
        now = datetime.now(UTC)
        payload = dict(job.payload or {})
        progress_data = payload.get("progress")
        if not isinstance(progress_data, dict):
            progress_data = {}
        progress_data["percentage"] = round(max(0.0, min(progress_percentage, 100.0)), 1)
        if isinstance(progress_step, str) and progress_step.strip():
            progress_data["step"] = progress_step.strip()
        progress_data["updated_at"] = now.isoformat()
        payload["progress"] = progress_data

        if isinstance(payload_extra, dict):
            payload.update(payload_extra)

        job.payload = payload

        if status is not None:
            job.status = status
            if status == JobStatus.IN_PROGRESS.value:
                if not job.started_at:
                    job.started_at = now
                job.attempts += 1
                job.error_payload = None
            elif status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
                job.completed_at = now
                if status == JobStatus.COMPLETED.value:
                    job.error_payload = None

        if error_payload is not None:
            job.error_payload = error_payload

        await self.session.commit()

    async def _extract_profile_signals(self, assessment_id: str) -> dict:
        """Extract profile signals from assessment responses."""
        stmt = (
            select(AssessmentQuestionSnapshot, AssessmentResponse)
            .join(
                AssessmentResponse,
                AssessmentResponse.question_snapshot_id == AssessmentQuestionSnapshot.id,
            )
            .where(
                AssessmentQuestionSnapshot.assessment_id == assessment_id,
                AssessmentQuestionSnapshot.question_type == QuestionType.PROFILE,
            )
        )
        rows = (await self.session.execute(stmt)).all()
        signals: dict[str, str | list[str] | int] = {}
        for snapshot, response in rows:
            response_data = response.response_data or {}
            key = str((snapshot.metadata_ or {}).get("dimension") or str(snapshot.sequence))

            project_count, project_contexts = self._extract_project_profile_payload(response_data)
            if key in {"experience-level", "experience"}:
                if project_count is not None:
                    signals["experience-project-count"] = project_count
                if project_contexts:
                    signals["experience-project-contexts"] = project_contexts

            # Check multiple possible keys for the response value
            # Q8 tech-preferences uses allow_custom which may store value differently
            value = (
                response_data.get("value")
                or response_data.get("selected_option")
                or response_data.get("answer")
                or response_data.get("answer_text")
                or response_data.get("custom_text")
                or response_data.get("text")
            )
            if value is None:
                continue

            if isinstance(value, list):
                cleaned = [str(item).strip() for item in value if str(item).strip()]
                if not cleaned:
                    continue
                signals[key] = cleaned
            else:
                text_value = str(value).strip()
                if not text_value:
                    continue
                signals[key] = text_value
        return signals

    async def _extract_essay_keywords(self, assessment_id: str) -> list[str]:
        """Extract keywords from essay responses/scores."""
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
        )
        rows = (await self.session.execute(stmt)).all()
        tokens: list[str] = []
        for _snapshot, response in rows:
            essay_text = response.response_data.get("answer", "")
            tokens.extend(self._tokenize(essay_text))
        counts = Counter(tokens)
        return [token for token, _count in counts.most_common(5)]

    async def _extract_missed_topics(self, assessment_id: str) -> list[str]:
        """Extract topics from questions that scored poorly."""
        profile_dimensions = {
            "experience",
            "experience-level",
            "tech-preferences",
            "content-duration",
            "payment-preference",
        }
        stmt = (
            select(Score, AssessmentQuestionSnapshot)
            .join(
                AssessmentQuestionSnapshot,
                AssessmentQuestionSnapshot.id == Score.question_snapshot_id,
            )
            .where(Score.assessment_id == assessment_id)
        )
        rows = (await self.session.execute(stmt)).all()
        missed: list[str] = []
        for score, snapshot in rows:
            if score.max_score <= 0:
                continue
            ratio = score.score / score.max_score
            if ratio >= 0.6:
                continue
            if snapshot.question_type == QuestionType.PROFILE:
                continue
            dimension = (snapshot.metadata_ or {}).get("dimension")
            if dimension and dimension not in profile_dimensions:
                missed.append(str(dimension))
        return missed

    async def _extract_score_metrics(self, assessment_id: str) -> dict[str, float | bool]:
        """Extract score percentages used for readiness/KKM gating."""
        stmt = select(Score).where(Score.assessment_id == assessment_id)
        result = await self.session.execute(stmt)
        scores = result.scalars().all()

        totals = {
            QuestionType.THEORETICAL: {"score": 0.0, "max": 0.0},
            QuestionType.PROFILE: {"score": 0.0, "max": 0.0},
            QuestionType.ESSAY: {"score": 0.0, "max": 0.0},
        }

        for score in scores:
            bucket = totals.get(score.question_type)
            if bucket is None:
                continue
            bucket["score"] += float(score.score or 0.0)
            bucket["max"] += float(score.max_score or 0.0)

        def pct(kind: QuestionType) -> float:
            max_val = totals[kind]["max"]
            if max_val <= 0:
                return 0.0
            return round((totals[kind]["score"] / max_val) * 100, 1)

        overall_score = sum(item["score"] for item in totals.values())
        overall_max = sum(item["max"] for item in totals.values())
        overall_pct = round((overall_score / overall_max) * 100, 1) if overall_max > 0 else 0.0

        return {
            "theoretical_pct": pct(QuestionType.THEORETICAL),
            "profile_pct": pct(QuestionType.PROFILE),
            "essay_pct": pct(QuestionType.ESSAY),
            "overall_score": round(overall_score, 1),
            "overall_max": round(overall_max, 1),
            "overall_pct": overall_pct,
            "has_essay_scores": totals[QuestionType.ESSAY]["max"] > 0,
        }

    async def _persist_recommendation_items(
        self,
        assessment_id: str,
        rag_result: RAGResult,
    ) -> None:
        """Persist RAG results as recommendation items."""
        # Check if recommendation exists
        stmt = select(Recommendation).where(Recommendation.assessment_id == assessment_id)
        result = await self.session.execute(stmt)
        recommendation = result.scalar_one_or_none()

        if not recommendation:
            # Create recommendation (will be fully populated by fusion)
            recommendation = Recommendation(
                assessment_id=assessment_id,
                summary="Pending fusion processing",
                overall_score=0.0,
                degraded=rag_result.degraded,
                rag_query=rag_result.query,
                rag_traces={
                    "match_count": len(rag_result.matches),
                    "degraded": rag_result.degraded,
                    "error": rag_result.error,
                    "readiness": rag_result.readiness,
                },
            )
            self.session.add(recommendation)
            await self.session.flush()
        else:
            recommendation.rag_query = rag_result.query
            recommendation.degraded = rag_result.degraded or recommendation.degraded
            recommendation.rag_traces = {
                "match_count": len(rag_result.matches),
                "degraded": rag_result.degraded,
                "error": rag_result.error,
                "readiness": rag_result.readiness,
            }
            # Prevent item duplication when RAG is reprocessed for the same assessment.
            await self.session.execute(
                delete(RecommendationItem).where(
                    RecommendationItem.recommendation_id == recommendation.id
                )
            )

        # Add recommendation items
        for i, match in enumerate(rag_result.matches, start=1):
            item = RecommendationItem(
                recommendation_id=recommendation.id,
                rank=i,
                course_id=match.course_id,
                course_title=match.title,
                course_url=match.url,
                relevance_score=match.relevance_score,
                match_reason=match.match_reason,
                course_metadata=match.metadata,
            )
            self.session.add(item)
