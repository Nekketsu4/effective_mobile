import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from app.config import settings


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


def create_token(user_id: str, expires_in_seconds: int = None):
    if expires_in_seconds is None:
        expires_in_seconds = settings.JWT_EXPIRES_SECONDS

    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    }
    return pyjwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise TokenExpiredError("Токен истек")
    except pyjwt.InvalidTokenError:
        raise TokenInvalidError("Не валидный токен")