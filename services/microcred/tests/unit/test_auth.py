from src.core.auth import create_access_token, decode_access_token


def test_create_and_decode_token_roundtrip() -> None:
    token = create_access_token("user-123", roles=["student"], email="user@example.com")

    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["roles"] == ["student"]
    assert payload["email"] == "user@example.com"
