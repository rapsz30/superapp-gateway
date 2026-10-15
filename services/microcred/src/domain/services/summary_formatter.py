from __future__ import annotations

from collections.abc import Iterable

from src.infrastructure.db.models import RecommendationItem


def _format_pts(value: float) -> str:
    """Format score in points."""
    return f"{float(value):.1f} pts"


def _format_pts_with_total(value: float, total: float | None) -> str:
    """Format score with denominator when available."""
    if isinstance(total, int | float) and float(total) > 0:
        return f"{float(value):.1f} / {float(total):.1f} pts"
    return _format_pts(value)


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


def _clean_text_list(value: object) -> list[str]:
    if isinstance(value, list | tuple | set):
        raw_values = value
    elif value is None:
        raw_values = []
    else:
        raw_values = [value]

    cleaned: list[str] = []
    for item in raw_values:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _format_project_context(context: str) -> str:
    mapping = {
        "personal": "personal projects",
        "kampus": "campus/bootcamp projects",
        "production": "production projects",
        "lintas-domain": "cross-domain projects",
    }
    normalized = context.strip().lower()
    return mapping.get(normalized, context.strip())


def _threshold_pct_to_pts(value_pct: object, overall_max_value: float | None) -> float | None:
    if not isinstance(value_pct, int | float):
        return None
    pct_value = float(value_pct)
    if overall_max_value is not None and overall_max_value > 0:
        return (pct_value / 100.0) * overall_max_value
    return pct_value


def _build_threshold_breakdown_text(
    readiness: dict | None,
    overall_max_value: float | None,
) -> str:
    """Build human-readable threshold adjustment breakdown."""
    if not isinstance(readiness, dict):
        return ""

    base_pct = readiness.get("base_advanced_threshold_pct")
    admin_base_pct = readiness.get("admin_base_advanced_threshold_pct")
    final_pct = readiness.get("advanced_threshold_pct", readiness.get("advanced_kkm"))
    adjustments = readiness.get("threshold_adjustments")
    if not isinstance(adjustments, dict):
        adjustments = {}

    target_base_adjustment_pct = float(adjustments.get("target_base_adjustment", 0.0) or 0.0)
    complexity_pct = float(adjustments.get("complexity", 0.0) or 0.0)
    prerequisite_pct = float(adjustments.get("prerequisite_gap", 0.0) or 0.0)
    experience_bonus_pct = float(adjustments.get("experience_bonus", 0.0) or 0.0)

    base_pts = _threshold_pct_to_pts(base_pct, overall_max_value)
    admin_base_pts = _threshold_pct_to_pts(admin_base_pct, overall_max_value)
    target_base_adjustment_pts = _threshold_pct_to_pts(
        target_base_adjustment_pct,
        overall_max_value,
    )
    final_pts = _threshold_pct_to_pts(final_pct, overall_max_value)
    complexity_pts = _threshold_pct_to_pts(complexity_pct, overall_max_value)
    prerequisite_pts = _threshold_pct_to_pts(prerequisite_pct, overall_max_value)
    experience_bonus_pts = _threshold_pct_to_pts(experience_bonus_pct, overall_max_value)

    if base_pts is None or final_pts is None:
        return ""

    if (
        admin_base_pts is not None
        and abs(target_base_adjustment_pct) > 0
        and target_base_adjustment_pts is not None
    ):
        base_segment = (
            f"admin base **{_format_pts(admin_base_pts)}** + target-level adjustment "
            f"**{_format_pts(target_base_adjustment_pts)}** = target-adjusted base "
            f"**{_format_pts(base_pts)}**"
        )
    else:
        base_segment = f"base **{_format_pts(base_pts)}**"

    return (
        "Threshold breakdown: "
        f"{base_segment} + complexity **+{_format_pts(complexity_pts or 0.0)}** "
        f"+ prerequisite gap **+{_format_pts(prerequisite_pts or 0.0)}** "
        f"- experience bonus **{_format_pts(experience_bonus_pts or 0.0)}** "
        f"= final threshold **{_format_pts(final_pts)}**."
    )


def format_assessment_summary(
    role_title: str,
    overall_pct: float,
    theoretical_pct: float,
    profile_pct: float,
    essay_pct: float,
    has_essay: bool,
    recommendations: Iterable[RecommendationItem],
    degraded: bool,
    profile_signals: dict | None = None,
    missed_topics: list[str] | None = None,
    user_name: str | None = None,
    readiness: dict | None = None,
    overall_score: float | None = None,
    overall_max: float | None = None,
    theoretical_score: float | None = None,
    profile_score: float | None = None,
    essay_score: float | None = None,
) -> str:
    """Build a markdown summary for assessment results.

    Args:
        role_title: The assessment role title
        overall_pct: Overall score percentage
        overall_score: Overall score in points
        overall_max: Maximum possible overall score
        theoretical_pct: Theoretical questions score percentage
        theoretical_score: Theoretical score in points
        profile_pct: Profile questions score percentage
        profile_score: Profile score in points
        essay_pct: Essay questions score percentage
        essay_score: Essay score in points
        has_essay: Whether assessment had essay questions
        recommendations: List of course recommendations
        degraded: Whether recommendations are in degraded mode
        profile_signals: Profile signals from profiling questions (Q7-Q10)
            - tech-preferences: What technologies/topics user wants to learn
            - content-duration: Preferred course duration (short/medium/long/any)
            - payment-preference: Payment preference (paid/free/any)
        missed_topics: List of topics where user scored poorly (weakness areas)
        user_name: User's display name for personalized greeting
    """
    lines: list[str] = []
    profile_signals = profile_signals or {}
    missed_topics = missed_topics or []
    display_overall = (
        float(overall_score) if isinstance(overall_score, int | float) else float(overall_pct)
    )
    display_theoretical = (
        float(theoretical_score)
        if isinstance(theoretical_score, int | float)
        else float(theoretical_pct)
    )
    display_profile = (
        float(profile_score) if isinstance(profile_score, int | float) else float(profile_pct)
    )
    display_essay = float(essay_score) if isinstance(essay_score, int | float) else float(essay_pct)
    overall_max_value = (
        float(overall_max)
        if isinstance(overall_max, int | float) and float(overall_max) > 0
        else None
    )

    # Extract tech preferences for personalized greeting
    tech_prefs_raw = profile_signals.get("tech-preferences", "")
    if isinstance(tech_prefs_raw, list):
        tech_prefs = ", ".join(str(item).strip() for item in tech_prefs_raw if str(item).strip())
    else:
        tech_prefs = str(tech_prefs_raw) if tech_prefs_raw is not None else ""

    # Build personalized greeting with name
    name_greeting = f"**Hello, {user_name}!** " if user_name else ""

    # Opening headline based on score with personalization
    if overall_pct >= 80:
        headline = (
            f"{name_greeting}**Excellent work!** You demonstrated strong capabilities "
            "for the "
            f"{role_title} role with an overall score of **{_format_pts(display_overall)}**."
        )
        if tech_prefs:
            headline += f" Your interest in learning **{tech_prefs}** is perfect for this stage."
    elif overall_pct >= 60:
        headline = (
            f"{name_greeting}**Good job!** Your assessment for the {role_title} role shows "
            f"a solid foundation. Overall score: **{_format_pts(display_overall)}**."
        )
        if tech_prefs:
            headline += f" Your focus on **{tech_prefs}** will help improve your skills."
    else:
        headline = (
            f"{name_greeting}**Thank you for completing the {role_title} assessment.** "
            f"Overall score: **{_format_pts(display_overall)}**."
        )
        if tech_prefs:
            headline += f" Your desire to learn **{tech_prefs}** is a great step forward!"

    lines.append(headline)
    lines.append("")

    # Detailed score breakdown with insights
    lines.append("**Score Breakdown & Insights**")
    lines.append("")

    # Theory analysis with actionable recommendations
    if theoretical_pct >= 80:
        theory_insight = (
            "Your theoretical understanding is excellent! "
            "You've mastered the fundamental concepts and are ready for real-world challenges. "
            "Consider advanced courses to deepen your expertise in specialization areas."
        )
    elif theoretical_pct >= 60:
        theory_insight = (
            "Your theoretical foundation is solid. To improve further, "
            "focus on areas where you scored lower and practice through hands-on "
            "projects. The courses below target your knowledge gaps."
        )
    else:
        theory_insight = (
            "Your theoretical foundation needs strengthening. "
            "Start with beginner-friendly courses that cover the fundamentals, "
            "then build up with practical exercises. "
            "Don't rush - mastering the fundamentals is key to long-term success."
        )
    lines.append(f"• **Theory:** {_format_pts(display_theoretical)}")
    lines.append(f"  {theory_insight}")
    lines.append("")

    # Essay quality analysis (if applicable) - includes missed topics feedback
    if has_essay:
        # Format missed topics for display in essay section
        missed_topics_text = ""
        if missed_topics:
            if len(missed_topics) == 1:
                missed_topics_text = f"**{missed_topics[0]}**"
            elif len(missed_topics) == 2:
                missed_topics_text = f"**{missed_topics[0]}** and **{missed_topics[1]}**"
            else:
                joined = ", ".join(missed_topics[:-1])
                missed_topics_text = f"**{joined}**, and **{missed_topics[-1]}**"

        if essay_pct >= 80:
            essay_insight = (
                "Excellent communication and problem-solving skills! "
                "Your answers demonstrate clear articulation of technical concepts, "
                "logical reasoning, and the ability to explain complex ideas effectively. "
                "These are valuable skills for collaboration and technical leadership roles."
            )
        elif essay_pct >= 60:
            if missed_topics:
                essay_insight = (
                    "Your explanations are quite good with clear understanding. "
                    "However, your essay answers show you could strengthen "
                    f"your understanding of {missed_topics_text}. "
                    "To improve, consider adding more specific examples "
                    "and deeper technical details in those areas. "
                    "Practicing technical documentation writing can help."
                )
            else:
                essay_insight = (
                    "Your explanations are quite good with clear understanding. "
                    "To improve, consider adding more specific examples, "
                    "deeper technical details, and more structured explanations. "
                    "Practicing technical documentation writing can help enhance this skill."
                )
        else:
            if missed_topics:
                essay_insight = (
                    "There's room to improve your ability to articulate "
                    "technical concepts. Your essay answers indicate gaps in "
                    f"understanding {missed_topics_text}. Focus on studying "
                    "these topics, organizing your thoughts logically, and "
                    "explaining the 'why' behind technical decisions. "
                    "Reading technical blogs and documentation can help."
                )
            else:
                essay_insight = (
                    "There's room to improve your ability to articulate technical concepts. "
                    "Focus on organizing your thoughts logically, providing specific "
                    "examples, and explaining the 'why' behind technical decisions. "
                    "Reading technical blogs and documentation can help improve this skill."
                )
        lines.append(f"• **Essay Quality:** {_format_pts(display_essay)}")
        lines.append(f"  {essay_insight}")
        lines.append("")

    # Extract user preferences for profile insight
    duration_pref_raw = profile_signals.get("content-duration", "any")
    if isinstance(duration_pref_raw, list):
        duration_pref_raw = duration_pref_raw[0] if duration_pref_raw else "any"
    duration_pref = str(duration_pref_raw).lower()

    payment_pref_raw = profile_signals.get("payment-preference", "any")
    if isinstance(payment_pref_raw, list):
        payment_pref_raw = payment_pref_raw[0] if payment_pref_raw else "any"
    payment_pref = str(payment_pref_raw).lower()

    # Map duration preference to readable text
    duration_text_map = {
        "short": "short courses (< 2 hours)",
        "medium": "medium-length courses (2-10 hours)",
        "long": "comprehensive/long courses (> 10 hours)",
        "any": "any duration",
    }
    duration_text = duration_text_map.get(duration_pref, "any duration")

    # Map payment preference to readable text
    payment_text_map = {
        "free": "free courses",
        "paid": "paid (premium) courses",
        "any": "both free and paid courses",
    }
    payment_text = payment_text_map.get(payment_pref, "both free and paid courses")

    # Profile Alignment - FINAL SECTION as conclusion
    # This discusses: experience/projects, tech preferences, duration, payment
    # Then concludes with WHY the recommendations are suitable

    # Build profile insight focusing on user's background and preferences
    profile_parts = []

    # Part 1: Experience level interpretation
    if profile_pct >= 80:
        exp_text = (
            f"With a profile score of **{_format_pts(display_profile)}**, you have significant "
            "experience "
            f"in the {role_title} field. Your coding journey and project portfolio "
            "demonstrate solid practical foundations."
        )
    elif profile_pct >= 60:
        exp_text = (
            f"With a profile score of **{_format_pts(display_profile)}**, you have moderate "
            "experience "
            f"as a {role_title}. You've started building your portfolio but there's "
            "room for more hands-on project experience."
        )
    else:
        exp_text = (
            f"With a profile score of **{_format_pts(display_profile)}**, "
            "you're at the beginning of your "
            f"{role_title} journey. Building more projects and gaining coding experience "
            "will strengthen your foundation."
        )
    profile_parts.append(exp_text)

    # Part 2: Tech preferences - Critical for personalization
    if tech_prefs and tech_prefs.strip():
        # Parse tech preferences (may be comma-separated)
        tech_list = [t.strip() for t in tech_prefs.split(",") if t.strip()]
        if tech_list:
            if len(tech_list) == 1:
                tech_display = f"**{tech_list[0]}**"
            elif len(tech_list) == 2:
                tech_display = f"**{tech_list[0]}** and **{tech_list[1]}**"
            else:
                tech_display = ", ".join(f"**{t}**" for t in tech_list[:-1])
                tech_display += f", and **{tech_list[-1]}**"

            tech_text = f"You've expressed interest in learning {tech_display}."
            profile_parts.append(tech_text)
    else:
        # User hasn't specified tech preferences - guide them
        tech_text = (
            "**Note:** You haven't specified which technologies you want to learn. "
            "Identifying your learning goals (e.g., Python, Docker, AWS) will help us "
            "provide more targeted course recommendations."
        )
        profile_parts.append(tech_text)

    # Extract Q7 structured profile signals (project count + contexts).
    project_count = _parse_non_negative_int(profile_signals.get("experience-project-count"))
    project_contexts = _clean_text_list(profile_signals.get("experience-project-contexts"))

    # Backward compatibility: some payloads may still keep this under experience-level dict.
    experience_payload = profile_signals.get("experience-level")
    if isinstance(experience_payload, dict):
        if project_count is None:
            project_count = _parse_non_negative_int(experience_payload.get("project_count"))
        if not project_contexts:
            project_contexts = _clean_text_list(
                experience_payload.get("selected_options")
                or experience_payload.get("project_contexts")
            )

    if project_count is not None or project_contexts:
        contexts_display = [_format_project_context(item) for item in project_contexts]
        if project_count is not None:
            count_text = f"**{project_count} projects**"
        else:
            count_text = "**multiple projects**"

        if contexts_display:
            if len(contexts_display) == 1:
                context_text = f" within **{contexts_display[0]}**"
            elif len(contexts_display) == 2:
                context_text = f" across **{contexts_display[0]}** and **{contexts_display[1]}**"
            else:
                context_text = (
                    " across **"
                    + ", ".join(contexts_display[:-1])
                    + f"**, and **{contexts_display[-1]}**"
                )
        else:
            context_text = ""

        profile_parts.append(
            f"From your **Q7 project experience**, you reported {count_text}{context_text}."
        )

    # Part 3: Learning preferences (duration + payment)
    if duration_pref != "any" or payment_pref != "any":
        pref_items = []
        if duration_pref != "any":
            pref_items.append(duration_text)
        if payment_pref != "any":
            pref_items.append(payment_text)
        pref_text = "Your learning preferences: " + ", ".join(pref_items) + "."
        profile_parts.append(pref_text)

    # Part 4: READINESS ASSESSMENT & CONCLUSION
    # Determine if user is ready for their desired tech or needs prerequisites
    has_valid_tech_prefs = tech_prefs and tech_prefs.strip()

    force_foundation = bool((readiness or {}).get("force_foundation"))
    readiness_reason = str((readiness or {}).get("reason") or "").strip()
    advanced_threshold = (readiness or {}).get(
        "advanced_threshold_pct", (readiness or {}).get("advanced_kkm")
    )
    learning_paths = (readiness or {}).get("learning_paths")
    learning_mode = str((learning_paths or {}).get("mode") or "")
    learning_paths_note = str((learning_paths or {}).get("note") or "").strip()
    target_coverage = (
        (readiness or {}).get("target_coverage") if isinstance(readiness, dict) else None
    )
    threshold_pct = (
        float(advanced_threshold) if isinstance(advanced_threshold, int | float) else None
    )
    threshold_display = (
        float((threshold_pct / 100.0) * overall_max_value)
        if threshold_pct is not None and overall_max_value is not None
        else threshold_pct
    )
    threshold_breakdown_text = _build_threshold_breakdown_text(readiness, overall_max_value)
    readiness_overall_pct = (readiness or {}).get("overall_pct")
    current_overall_pct = (
        float(readiness_overall_pct)
        if isinstance(readiness_overall_pct, int | float)
        else float(overall_pct)
    )
    readiness_overall_score = (readiness or {}).get("overall_score")
    current_overall_display = (
        float(readiness_overall_score)
        if isinstance(readiness_overall_score, int | float)
        else display_overall
    )

    if force_foundation and has_valid_tech_prefs:
        recommendation_text = (
            readiness_reason or "Complete Mandatory Foundation first, then continue to Target Path."
        )
        if threshold_pct is not None:
            threshold_text = _format_pts_with_total(
                threshold_display if threshold_display is not None else threshold_pct,
                overall_max_value,
            )
            kkm_text = f"Minimum readiness threshold: **{threshold_text}**."
            current_overall_text = _format_pts_with_total(
                current_overall_display,
                overall_max_value,
            )
            score_text = (
                f"Your current score is **{current_overall_text}**, " "so you are not ready yet."
            )
        else:
            kkm_text = "Your current score has not reached the readiness threshold."
            score_text = "Your current score indicates you should strengthen fundamentals first."
        readiness_assessment = (
            f"**Readiness Assessment:** For your target **{tech_prefs}**, {score_text} {kkm_text}"
        )
        if threshold_breakdown_text:
            readiness_assessment += f"\n{threshold_breakdown_text}"
        conclusion = (
            f"{readiness_assessment}\n\n"
            "**Action Priority:** Work on **Mandatory Foundation** first so your transition to "
            "advanced topics is safer and more effective.\n\n"
            "This decision combines your **theoretical**, **essay**, and **profile** performance. "
            f"**Recommendation:** {recommendation_text}"
        )
    elif has_valid_tech_prefs:
        tech_lower = tech_prefs.lower()

        # Define advanced topics that require strong fundamentals
        advanced_topics = [
            "kubernetes",
            "k8s",
            "microservices",
            "machine learning",
            "ml",
            "deep learning",
            "ai",
            "artificial intelligence",
            "docker",
            "terraform",
            "aws",
            "azure",
            "gcp",
            "cloud",
            "devops",
            "kafka",
            "redis",
            "elasticsearch",
            "graphql",
        ]

        # Define fundamental topics
        fundamental_topics = [
            "python",
            "javascript",
            "java",
            "html",
            "css",
            "sql",
            "git",
            "api",
            "rest",
            "database",
            "programming",
        ]

        is_advanced = any(adv in tech_lower for adv in advanced_topics)
        is_fundamental = any(fund in tech_lower for fund in fundamental_topics)

        # ADVANCED topics + LOW experience = Need prerequisites
        if is_advanced and profile_pct < 50 and theoretical_pct < 60:
            conclusion = (
                f"**Readiness Assessment:** Your interest in {tech_prefs} is excellent "
                "for long-term career growth! However, these are advanced topics that "
                "require solid programming fundamentals. "
                "**Recommendation:** The courses below focus on building strong foundations "
                f"(APIs, databases, backend basics). Master these first, then you'll be "
                f"ready to dive into {tech_prefs}. Estimated timeline: 3-6 months of foundation "
                "building before tackling advanced topics."
            )

        # ADVANCED topics + MODERATE experience = Can start with guided approach
        elif is_advanced and profile_pct >= 50 and theoretical_pct >= 60:
            conclusion = (
                f"**Readiness Assessment:** You have a decent foundation to start exploring "
                f"{tech_prefs}! Your theoretical knowledge "
                f"({_format_pts(display_theoretical)}) shows you "
                "understand core concepts. "
                "**Recommendation:** The courses below include both foundational reinforcement "
                f"and introductory {tech_prefs} content. Take them in sequence to build "
                "confidence before diving into advanced implementations."
            )

        # FUNDAMENTAL topics + ANY level = Good match
        elif is_fundamental:
            if profile_pct >= 60:
                conclusion = (
                    f"**Readiness Assessment:** Perfect match! Your experience level "
                    f"and interest in {tech_prefs} align well. "
                    "**Recommendation:** The courses below will deepen your expertise "
                    "in these core technologies and introduce advanced patterns."
                )
            else:
                conclusion = (
                    f"**Readiness Assessment:** Great choice! {tech_prefs} are fundamental "
                    "technologies that every developer should master. "
                    "**Recommendation:** The courses below are designed for beginners "
                    "and will build your skills step by step. Focus on hands-on practice "
                    "alongside these courses."
                )

        # HIGH experience + ANY tech = Ready
        elif profile_pct >= 80:
            conclusion = (
                f"**Readiness Assessment:** You're ready to pursue {tech_prefs}! "
                "Your strong experience provides a solid base for learning new technologies. "
                "**Recommendation:** The courses below match your goals and will help you "
                "specialize quickly. Consider building projects as you learn."
            )

        # Default case
        else:
            conclusion = (
                f"**Readiness Assessment:** You're on the right path to learning {tech_prefs}. "
                "**Recommendation:** The courses below are curated based on your experience level "
                "and learning goals. Start with foundational courses, then progressively tackle "
                "more advanced topics."
            )

    else:
        # No tech preferences specified
        conclusion = (
            "**Recommendation:** Since you haven't specified your technology interests yet, "
            "the courses below cover general fundamentals for the " + role_title + " role. "
            "Once you identify specific technologies you want to learn, we can provide "
            "more targeted recommendations that match your career goals."
        )
    profile_parts.append(conclusion)

    profile_insight = " ".join(profile_parts)

    lines.append(f"• **Profile Alignment:** {_format_pts(display_profile)}")
    lines.append(f"  {profile_insight}")
    lines.append("")

    # Personalized learning path recommendations
    def append_recommendation_items(path_recs: list[RecommendationItem]) -> None:
        """Append recommendation items with details and preference match notes."""
        for idx, rec in enumerate(path_recs[:5], start=1):
            lines.append(f"{idx}. **{rec.course_title}**")

            if rec.match_reason:
                lines.append(f"   • Recommendation reason: {rec.match_reason}")

            metadata = rec.course_metadata or {}
            personalization_matches = []

            if tech_prefs:
                course_title_lower = str(rec.course_title or "").lower()
                tech_keywords = [t.strip().lower() for t in tech_prefs.replace(",", " ").split()]
                matched_techs = [t for t in tech_keywords if t in course_title_lower]
                if matched_techs:
                    personalization_matches.append("Matches interest: " + ", ".join(matched_techs))

            level = str(metadata.get("level", "")).lower()
            if duration_pref == "short" and "beginner" in level:
                personalization_matches.append("Suitable for beginners (short duration)")
            elif duration_pref == "medium" and "intermediate" in level:
                personalization_matches.append("Intermediate level matches preference")
            elif duration_pref == "long" and ("advanced" in level or "all levels" in level):
                personalization_matches.append("Comprehensive/advanced content matches preference")

            is_paid = str(metadata.get("is_paid", "True")).lower() == "true"
            if payment_pref == "free" and not is_paid:
                personalization_matches.append("Free as preferred")
            elif payment_pref == "paid" and is_paid:
                personalization_matches.append("Premium course as preferred")

            if personalization_matches:
                lines.append("   • Preference match: " + "; ".join(personalization_matches))

            if level:
                lines.append(f"   • Difficulty level: {level.title()}")

            rel_score = rec.relevance_score
            if rel_score >= 0.8:
                rel_text = f"{rel_score:.2f}/1.0 (Highly Relevant)"
            elif rel_score >= 0.6:
                rel_text = f"{rel_score:.2f}/1.0 (Relevant)"
            else:
                rel_text = f"{rel_score:.2f}/1.0 (Somewhat Relevant)"
            lines.append(f"   • Match score: {rel_text}")
            lines.append("")

    recs = list(recommendations)
    if recs:
        lines.append("")
        lines.append("**Personalized Learning Path**")
        lines.append("")
        lines.append(
            "Recommendations are ranked using your **theoretical**, **essay**, and **profile** "
            "results, then filtered by your **payment** and **content duration** preferences."
        )
        lines.append("")
        if learning_paths_note:
            lines.append(learning_paths_note)
            lines.append("")

        if isinstance(target_coverage, dict):
            target_keywords = target_coverage.get("target_keywords")
            covered_keywords = target_coverage.get("covered_keywords")
            missing_keywords = target_coverage.get("missing_keywords")
            catalog_missing_keywords = target_coverage.get("catalog_missing_keywords")
            coverage_ratio = target_coverage.get("coverage_ratio")
            coverage_percentage = target_coverage.get("coverage_percentage")
            target_count = target_coverage.get("target_count")
            covered_count_raw = target_coverage.get("covered_count")

            if isinstance(target_keywords, list) and target_keywords:
                resolved_target_count = (
                    int(target_count)
                    if isinstance(target_count, int | float) and int(target_count) > 0
                    else len(target_keywords)
                )
                covered_count = (
                    int(covered_count_raw)
                    if isinstance(covered_count_raw, int | float)
                    else (
                        len(covered_keywords)
                        if isinstance(covered_keywords, list)
                        else int(round(float(coverage_ratio or 0.0) * resolved_target_count))
                    )
                )
                coverage_pct_display = (
                    float(coverage_percentage)
                    if isinstance(coverage_percentage, int | float)
                    else round((covered_count / resolved_target_count) * 100.0, 1)
                )
                coverage_text = (
                    f"{covered_count}/{resolved_target_count} keywords "
                    f"({coverage_pct_display:.1f}%)"
                )
                lines.append("Target coverage in current recommendations: " f"**{coverage_text}**.")
                if isinstance(catalog_missing_keywords, list) and catalog_missing_keywords:
                    lines.append(
                        "Unavailable in current catalog: "
                        + ", ".join(str(item) for item in catalog_missing_keywords)
                        + "."
                    )
                if (
                    isinstance(missing_keywords, list)
                    and missing_keywords
                    and not (
                        isinstance(catalog_missing_keywords, list) and len(catalog_missing_keywords)
                    )
                ):
                    lines.append(
                        "Not yet matched in top recommendations: "
                        + ", ".join(str(item) for item in missing_keywords)
                        + "."
                    )
                lines.append("")

        mandatory_recs: list[RecommendationItem] = []
        target_recs: list[RecommendationItem] = []
        fallback_recs: list[RecommendationItem] = []
        for rec in recs:
            metadata = rec.course_metadata or {}
            learning_path = str(metadata.get("learning_path") or "").strip().lower()
            if learning_path == "mandatory_foundation":
                mandatory_recs.append(rec)
            elif learning_path == "target_path":
                target_recs.append(rec)
            else:
                fallback_recs.append(rec)

        # Add personalized intro based on overall performance and readiness mode.
        rendered_two_path = False
        if learning_mode == "two-path" and (mandatory_recs or target_recs):
            rendered_two_path = True
            if threshold_pct is not None and current_overall_pct < threshold_pct:
                threshold_text = _format_pts_with_total(
                    threshold_display if threshold_display is not None else threshold_pct,
                    overall_max_value,
                )
                current_overall_text = _format_pts_with_total(
                    current_overall_display,
                    overall_max_value,
                )
                path_intro = (
                    f"Your current score is **{current_overall_text}**, below "
                    "the minimum "
                    f"readiness threshold (**{threshold_text}**). "
                    "Prioritize **Mandatory Foundation** "
                    "first, then continue to **Target Path** once your fundamentals are stronger."
                )
            elif threshold_pct is not None:
                threshold_text = _format_pts_with_total(
                    threshold_display if threshold_display is not None else threshold_pct,
                    overall_max_value,
                )
                current_overall_text = _format_pts_with_total(
                    current_overall_display,
                    overall_max_value,
                )
                path_intro = (
                    f"Your score (**{current_overall_text}**) has reached "
                    "the minimum "
                    f"readiness threshold (**{threshold_text}**). You can progress through both "
                    "paths in sequence."
                )
            else:
                path_intro = (
                    "This plan is split into two tracks: **Mandatory Foundation** and "
                    "**Target Path**. Finish foundation first to reduce learning risk."
                )
            lines.append(path_intro)
            if threshold_breakdown_text:
                lines.append(threshold_breakdown_text)
            lines.append("")

            lines.append("**Mandatory Foundation (Top 5)**")
            lines.append("")
            if mandatory_recs:
                append_recommendation_items(mandatory_recs)
            else:
                lines.append("No mandatory foundation courses were found for this attempt.")
                lines.append("")

            lines.append("**Target Path (Top 5)**")
            lines.append("")
            if target_recs:
                append_recommendation_items(target_recs)
            else:
                lines.append("No target path courses were found for this attempt.")
                lines.append("")

            if fallback_recs:
                lines.append("**Additional Recommendations**")
                lines.append("")
                append_recommendation_items(fallback_recs)
        elif overall_pct >= 80:
            if tech_prefs:
                path_intro = (
                    f"Based on your strong performance and interest in **{tech_prefs}**, "
                    f"these advanced courses will help you reach expert level as a {role_title}:"
                )
            else:
                path_intro = (
                    f"Based on your strong performance, these advanced courses will help you "
                    f"specialize and reach expert level as a {role_title}:"
                )
        elif overall_pct >= 60:
            if tech_prefs:
                path_intro = (
                    f"To grow from your intermediate level and master **{tech_prefs}**, "
                    f"these courses target your growth areas:"
                )
            else:
                path_intro = (
                    "To grow from your intermediate level, these courses target "
                    "your growth areas and build on your existing strengths:"
                )
        else:
            if tech_prefs:
                path_intro = (
                    f"To build a strong foundation towards **{tech_prefs}**, start with "
                    f"these courses suited to your level that will gradually develop your skills:"
                )
            else:
                path_intro = (
                    "To build a strong foundation, start with these courses suited "
                    "to your level that will gradually develop your skills:"
                )

        if not rendered_two_path:
            lines.append(path_intro)
            lines.append("")
            append_recommendation_items(recs)

    if degraded:
        lines.append("")
        lines.append(
            "_Note: Some recommendations may be limited due to temporary service constraints._"
        )

    return "\n".join(lines)
