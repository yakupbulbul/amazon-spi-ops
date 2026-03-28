from datetime import timedelta

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip() -> None:
    password = "test-password-123"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True
    assert verify_password("wrong-password", hashed_password) is False


def test_access_token_round_trip() -> None:
    token = create_access_token(subject="user-id", expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)

    assert payload["sub"] == "user-id"
