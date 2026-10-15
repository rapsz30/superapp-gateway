from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi.testclient import TestClient
from src.api.deps import issue_smoke_token
from src.core.auth import Role


def auth_headers(user_id: str = "student-1", role: Role = Role.STUDENT) -> dict[str, str]:
    token = issue_smoke_token(user_id, role=role, email="student@example.com")
    return {"Authorization": f"Bearer {token}"}


def build_responses_payload(
    questions: Sequence[dict[str, Any]],
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Construct a JSON payload for POST /assessments/{id}/submit."""
    overrides = overrides or {}
    responses: list[dict[str, Any]] = []

    for question in questions:
        qid = question["id"]
        data = {"question_id": qid}
        override = overrides.get(qid)
        if override:
            data.update(override)
        else:
            qtype = question["question_type"]
            sequence = question["sequence"]
            if qtype == "theoretical":
                data["selected_option"] = "A"
            elif qtype == "essay":
                data["answer_text"] = f"Sample essay response {sequence}"
            else:  # profile
                expected_values = question.get("expected_values") or {}
                if (
                    isinstance(expected_values, dict)
                    and expected_values.get("type") == "project_checklist"
                ):
                    data["project_count"] = 10
                    data["selected_options"] = [
                        "personal",
                        "kampus",
                        "production",
                        "lintas-domain",
                    ]
                    data["value"] = "10"
                    responses.append(data)
                    continue

                accepted = None
                metadata = question.get("metadata") or {}
                if isinstance(metadata, dict):
                    accepted = metadata.get("accepted_values")
                if isinstance(accepted, list) and accepted:
                    data["value"] = str(accepted[0])
                else:
                    data["value"] = f"Sample profile answer {sequence}"
        responses.append(data)

    return {"responses": responses}


def submit_with_payload(
    client: TestClient,
    assessment_id: str,
    questions: Sequence[dict[str, Any]],
    headers: dict[str, str],
    overrides: dict[str, dict[str, Any]] | None = None,
):
    payload = build_responses_payload(questions, overrides=overrides)
    return client.post(
        f"/assessments/{assessment_id}/submit",
        headers=headers,
        json=payload,
    )
