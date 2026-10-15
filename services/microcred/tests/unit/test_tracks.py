from __future__ import annotations


def test_tracks_endpoint_returns_seeded_roles(test_client_with_questions) -> None:
    response = test_client_with_questions.get("/tracks")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tracks"]) >= 2
    backend = next(track for track in payload["tracks"] if track["slug"] == "backend-engineer")
    assert backend["question_count"] == 10
