"""Хэширование паролей и токены доступа. Проверка ролей – app.modules.auth.dependencies."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings

_ITER = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITER).hex()
    return f"pbkdf2_sha256${_ITER}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters)).hex()
    return hmac.compare_digest(check, digest)


def create_token(login: str) -> str:
    payload = {"sub": login, "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.token_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> str | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        return None
