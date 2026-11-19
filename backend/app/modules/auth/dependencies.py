"""Разграничение доступа по ролям (подсистема «Доступ и безопасность», Т13). Используется всеми модулями."""
from fastapi import Cookie, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_token

from .models import UserAccount

ROLE_NAMES = {
    "OPERATOR": "Оператор регистратуры",
    "DOCTOR": "Врач-специалист",
    "NURSE": "Медицинская сестра",
    "PATIENT": "Пациент",
    "LAB": "Сотрудник лаборатории",
    "ADMIN": "Администратор клиники",
}


def current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    token_cookie: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> UserAccount:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    elif token_cookie:
        token = token_cookie
    if not token:
        raise Unauthorized("Требуется вход в систему")
    login = decode_token(token)
    if not login:
        raise Unauthorized("Сеанс истёк, войдите снова")
    user = db.get(UserAccount, login)
    if not user or not user.is_active:
        raise Unauthorized("Учётная запись недоступна")
    return user


def require_roles(*roles: str):
    """Зависимость FastAPI: пускает только пользователей указанных ролей (И1)."""

    def checker(user: UserAccount = Depends(current_user)) -> UserAccount:
        if user.role_code not in roles:
            raise Forbidden("Нет прав на эту операцию для роли «%s»" % ROLE_NAMES.get(user.role_code, user.role_code))
        return user

    return checker
