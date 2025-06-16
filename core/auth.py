import os
from datetime import timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

_SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
_SERIALIZER = URLSafeTimedSerializer(_SECRET_KEY)
_TOKEN_TTL = int(os.environ.get("TOKEN_TTL", "3600"))


def issue_token(user_id: int) -> str:
    """Return a signed token for the given user id."""
    return _SERIALIZER.dumps({"user_id": user_id})


def verify_token(token: str) -> int | None:
    """Validate a token and return the embedded user id if valid."""
    try:
        data = _SERIALIZER.loads(token, max_age=_TOKEN_TTL)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("user_id")
