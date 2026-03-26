import pytest
import time

import jwt as pyjwt

from app.utils.jwt import create_token, decode_token
from app.utils.jwt import TokenExpiredError, TokenInvalidError


def test_token_contains_user_id():
    token = create_token(user_id="user123")
    payload = decode_token(token)
    assert payload["sub"] == "user123"


def test_expired_token_raises_error():
    token = create_token(user_id="user123", expires_in_seconds=0)
    time.sleep(1)
    with pytest.raises(TokenExpiredError):
        decode_token(token)


def test_tampered_token_raises_error():
    token = create_token(user_id="user123")
    tampered_token = token + "tampered"
    with pytest.raises(TokenInvalidError):
        decode_token(tampered_token)


def test_token_with_wrong_secret_raises_error():
    fake_token = pyjwt.encode(
        {"user_id": "user123"}, "wrong-secret" * 8, algorithm="HS256"
    )
    with pytest.raises(TokenInvalidError):
        decode_token(fake_token)
