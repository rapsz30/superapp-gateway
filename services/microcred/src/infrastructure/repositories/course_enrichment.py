"""
Course Enrichment Module for Comprehensive Content-Based Filtering.

Maps raw course data to rich metadata for better recommendation matching.
Includes tech tags, difficulty mapping, payment type, duration categories, etc.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# Technology/Framework keyword mapping
# Maps course title keywords to standardized tech tags
TECH_KEYWORD_MAP: dict[str, list[str]] = {
    # Programming Languages
    "python": ["python", "django", "flask", "fastapi", "pandas", "numpy", "pytorch", "tensorflow"],
    "javascript": ["javascript", "js", "node", "nodejs", "express", "nest"],
    "typescript": ["typescript", "ts"],
    "golang": ["golang", "go programming", " go ", "go lang"],
    "java": ["java", "spring", "spring boot", "hibernate"],
    "php": ["php", "laravel", "symfony", "wordpress"],
    "ruby": ["ruby", "rails", "ruby on rails"],
    "csharp": ["c#", "csharp", ".net", "dotnet", "asp.net"],
    "rust": ["rust programming", "rust lang"],
    "kotlin": ["kotlin"],
    "swift": ["swift", "ios"],
    # Frontend Technologies
    "react": ["react", "reactjs", "react.js", "next.js", "nextjs"],
    "vue": ["vue", "vuejs", "vue.js", "nuxt"],
    "angular": ["angular", "angularjs"],
    "svelte": ["svelte"],
    # Backend/Architecture
    "microservices": ["microservice", "microservices", "micro service"],
    "api": ["api", "rest api", "restful", "graphql"],
    "grpc": ["grpc", "protocol buffer"],
    "websocket": ["websocket", "ws"],
    # Databases
    "postgresql": ["postgresql", "postgres", "pg"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis", "cache"],
    "elasticsearch": ["elasticsearch", "elastic"],
    "cassandra": ["cassandra"],
    "dynamodb": ["dynamodb"],
    # DevOps/Infrastructure
    "docker": ["docker", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "jenkins": ["jenkins"],
    "cicd": ["ci/cd", "continuous integration", "continuous deployment"],
    # Data/ML
    "machine-learning": ["machine learning", "ml", "deep learning", "neural network"],
    "data-science": ["data science", "data analysis", "data analytics"],
    "big-data": ["big data", "spark", "hadoop"],
    "ai": ["artificial intelligence", "ai"],
    "sql": ["sql", "sql server", "t-sql", "postgresql", "postgres", "mysql", "sqlite"],
    "excel": ["excel", "spreadsheet", "spreadsheets"],
    "power-bi": ["power bi", "powerbi", "power-bi"],
    "tableau": ["tableau"],
    "data-visualization": [
        "data visualization",
        "visualization",
        "dataviz",
        "dashboard",
        "dashboards",
        "d3",
        "d3.js",
    ],
    "data-analysis": ["data analysis", "data analytics", "analytics"],
    "statistics": ["statistics", "statistical"],
    # Testing/Quality
    "testing": ["test", "testing", "unit test", "integration test"],
    "pytest": ["pytest"],
    "jest": ["jest"],
    "cypress": ["cypress"],
    # Security
    "security": ["security", "cybersecurity", "oauth", "jwt"],
    "authentication": ["authentication", "auth", "authorization"],
    # Soft Skills
    "agile": ["agile", "scrum", "kanban"],
    "product-management": ["product management", "product manager"],
}

# Subject to tech tags mapping (for courses without specific keywords in title)
SUBJECT_TECH_MAP: dict[str, list[str]] = {
    "Web Development": ["javascript", "html", "css", "react", "api"],
    "Business Finance": ["finance", "business", "accounting", "data-analysis", "excel"],
    "Musical Instruments": ["music", "instruments"],
    "Graphic Design": ["design", "photoshop", "illustrator"],
}

# Difficulty level normalization
DIFFICULTY_MAP: dict[str, str] = {
    "All Levels": "beginner",  # Accessible to all = beginner-friendly
    "Beginner Level": "beginner",
    "Intermediate Level": "intermediate",
    "Expert Level": "advanced",
}

# Duration categories (in hours)
DurationCategory = Literal["short", "medium", "long", "very_long"]


@dataclass
class EnrichedCourseMetadata:
    """Enriched metadata for a course."""

    course_id: str
    title: str

    # Tech tags extracted from title + subject
    tech_tags: list[str]

    # Normalized difficulty
    difficulty: str  # beginner, intermediate, advanced

    # Payment info
    is_free: bool
    payment_type: str  # "free" or "paid"
    price: float

    # Duration category
    duration_hours: float
    duration_category: DurationCategory

    # Quality metrics
    num_subscribers: int
    num_reviews: int
    num_lectures: int

    # Computed scores
    quality_score: float
    popularity_score: float
    engagement_score: float

    # Raw data
    level: str
    subject: str
    url: str
    published_timestamp: str


class CourseEnricher:
    """Enrich courses with comprehensive metadata for better CBF matching."""

    @staticmethod
    def normalize_term(term: str) -> str:
        """Normalize term for matching by removing non-alphanumerics."""
        return re.sub(r"[^a-z0-9]+", "", term.lower())

    @staticmethod
    def extract_tech_tags(title: str, subject: str) -> list[str]:
        """Extract tech tags from course title and subject.

        Uses whole-word matching to avoid false positives.
        Example: 'api' should not match 'Instagram'
        """
        tags: set[str] = set()

        # Normalize text for matching
        text = f"{title} {subject}".lower()

        # Check each tech keyword
        for tech_tag, keywords in TECH_KEYWORD_MAP.items():
            for keyword in keywords:
                # Use word boundary matching for accuracy
                pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
                if re.search(pattern, text):
                    tags.add(tech_tag)
                    break  # One match per tech tag is enough

        # Add subject-based tags if no specific tech tags found
        if not tags:
            subject_tags = SUBJECT_TECH_MAP.get(subject, [])
            tags.update(subject_tags[:2])  # Limit to 2 generic tags

        return sorted(list(tags))

    @staticmethod
    def normalize_difficulty(level: str) -> str:
        """Normalize difficulty level to: beginner, intermediate, advanced."""
        return DIFFICULTY_MAP.get(level, "intermediate")

    @staticmethod
    def categorize_duration(hours: float) -> DurationCategory:
        """Categorize course duration.

        - short: < 5 hours (quick courses)
        - medium: 5-20 hours (typical courses)
        - long: 20-50 hours (comprehensive)
        - very_long: > 50 hours (bootcamp-style)
        """
        if hours < 5:
            return "short"
        elif hours < 20:
            return "medium"
        elif hours < 50:
            return "long"
        else:
            return "very_long"

    @staticmethod
    def compute_quality_score(
        num_subscribers: int,
        num_reviews: int,
        num_lectures: int,
        content_duration: float,
    ) -> float:
        """Compute overall quality score (0-1).

        Factors:
        - Popularity (subscribers)
        - Engagement (reviews / subscribers ratio)
        - Content depth (lectures + duration)
        """
        # Popularity component (0-0.4)
        popularity = min(0.4, num_subscribers / 50000)

        # Review count component (0-0.2)
        review_score = min(0.2, num_reviews / 2000)

        # Engagement ratio (reviews per subscriber)
        if num_subscribers > 0:
            engagement_ratio = num_reviews / num_subscribers
            engagement = min(0.2, engagement_ratio * 5)
        else:
            engagement = 0

        # Content depth (lectures + duration)
        depth = min(0.2, (num_lectures / 200) * 0.1 + (content_duration / 50) * 0.1)

        return popularity + review_score + engagement + depth

    @staticmethod
    def compute_popularity_score(num_subscribers: int) -> float:
        """Compute popularity score (0-1) based on subscribers."""
        return min(1.0, num_subscribers / 100000)

    @staticmethod
    def compute_engagement_score(num_subscribers: int, num_reviews: int) -> float:
        """Compute engagement score (0-1) based on review ratio."""
        if num_subscribers == 0:
            return 0.0

        ratio = num_reviews / num_subscribers
        # Typical good ratio is 0.02 (2% of students leave reviews)
        return min(1.0, ratio / 0.02)

    @classmethod
    def enrich_course(cls, course_dict: dict) -> EnrichedCourseMetadata:
        """Enrich a single course dictionary with comprehensive metadata."""
        # Extract basic info
        course_id = course_dict.get("course_id", "")
        title = course_dict.get("course_title", "")
        subject = course_dict.get("subject", "")
        level = course_dict.get("level", "All Levels")
        url = course_dict.get("url", "")
        published_timestamp = course_dict.get("published_timestamp", "")

        # Parse numeric fields safely
        try:
            is_paid = course_dict.get("is_paid", "False").lower() in ("true", "1", "yes")
        except AttributeError:
            is_paid = bool(course_dict.get("is_paid", False))

        try:
            price = float(course_dict.get("price", 0) or 0)
        except (ValueError, TypeError):
            price = 0.0

        try:
            num_subscribers = int(course_dict.get("num_subscribers", 0) or 0)
        except (ValueError, TypeError):
            num_subscribers = 0

        try:
            num_reviews = int(course_dict.get("num_reviews", 0) or 0)
        except (ValueError, TypeError):
            num_reviews = 0

        try:
            num_lectures = int(course_dict.get("num_lectures", 0) or 0)
        except (ValueError, TypeError):
            num_lectures = 0

        try:
            content_duration = float(course_dict.get("content_duration", 0) or 0)
        except (ValueError, TypeError):
            content_duration = 0.0

        # Extract tech tags
        tech_tags = cls.extract_tech_tags(title, subject)

        # Normalize difficulty
        difficulty = cls.normalize_difficulty(level)

        # Payment type
        payment_type = "paid" if is_paid else "free"

        # Duration category
        duration_category = cls.categorize_duration(content_duration)

        # Compute scores
        quality_score = cls.compute_quality_score(
            num_subscribers, num_reviews, num_lectures, content_duration
        )
        popularity_score = cls.compute_popularity_score(num_subscribers)
        engagement_score = cls.compute_engagement_score(num_subscribers, num_reviews)

        return EnrichedCourseMetadata(
            course_id=course_id,
            title=title,
            tech_tags=tech_tags,
            difficulty=difficulty,
            is_free=not is_paid,
            payment_type=payment_type,
            price=price,
            duration_hours=content_duration,
            duration_category=duration_category,
            num_subscribers=num_subscribers,
            num_reviews=num_reviews,
            num_lectures=num_lectures,
            quality_score=quality_score,
            popularity_score=popularity_score,
            engagement_score=engagement_score,
            level=level,
            subject=subject,
            url=url,
            published_timestamp=published_timestamp,
        )

    @classmethod
    def match_user_preferences(
        cls,
        enriched_course: EnrichedCourseMetadata,
        user_tech_prefs: list[str],
        payment_pref: str = "any",
        duration_pref: str = "any",
        difficulty_pref: str | None = None,
    ) -> tuple[bool, float]:
        """Check if course matches user preferences and return match score.

        Args:
            enriched_course: Course metadata
            user_tech_prefs: List of technologies user wants to learn
                (e.g., ['golang', 'microservices'])
            payment_pref: 'free', 'paid', or 'any'
            duration_pref: 'short', 'medium', 'long', or 'any'
            difficulty_pref: 'beginner', 'intermediate', 'advanced', or None

        Returns:
            (matches, match_score) - matches=True if course passes filters, score=0-1 relevance
        """
        # Payment filter
        if payment_pref != "any":
            if payment_pref == "free" and not enriched_course.is_free:
                return False, 0.0
            if payment_pref == "paid" and enriched_course.is_free:
                return False, 0.0

        # Duration filter
        if duration_pref != "any":
            if duration_pref != enriched_course.duration_category:
                # Allow adjacent categories (e.g., medium can match long)
                adjacent_map = {
                    "short": ["medium"],
                    "medium": ["short", "long"],
                    "long": ["medium", "very_long"],
                    "very_long": ["long"],
                }
                if enriched_course.duration_category not in adjacent_map.get(duration_pref, []):
                    return False, 0.0

        # Difficulty filter (if specified)
        if difficulty_pref and difficulty_pref != enriched_course.difficulty:
            # Allow beginner courses for any level (everyone can benefit from fundamentals)
            if enriched_course.difficulty != "beginner":
                return False, 0.0

        # Tech preference matching (most important)
        if not user_tech_prefs:
            # No tech preferences specified = accept any course
            match_score = 0.5
        else:
            # Count matching tech tags
            user_prefs_normalized = [
                cls.normalize_term(str(p)) for p in user_tech_prefs if str(p).strip()
            ]
            course_tags_normalized = {
                cls.normalize_term(t) for t in enriched_course.tech_tags if str(t).strip()
            }

            if not user_prefs_normalized:
                match_score = 0.5
            else:
                matches = sum(1 for pref in user_prefs_normalized if pref in course_tags_normalized)

                if matches == 0:
                    return False, 0.0  # No tech match = exclude

                # Match score based on overlap
                match_score = min(1.0, matches / len(user_prefs_normalized) * 0.7)

        # Boost score with quality metrics
        final_score = (
            match_score * 0.5  # 50% from tech match
            + enriched_course.quality_score * 0.3  # 30% from quality
            + enriched_course.popularity_score * 0.1  # 10% from popularity
            + enriched_course.engagement_score * 0.1  # 10% from engagement
        )

        return True, min(1.0, final_score)
