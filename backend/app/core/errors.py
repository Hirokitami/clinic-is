"""Ошибки предметной области. Ответ: {"detail": {"code": ..., "message": ..., ...доп. поля}}."""
from typing import Any

from fastapi import HTTPException


class AppError(HTTPException):
    status = 400
    default_code = "ERROR"

    def __init__(self, message: str, code: str | None = None, **extra: Any):
        super().__init__(self.status, {"code": code or self.default_code, "message": message, **extra})


class BadRequest(AppError):
    status = 400
    default_code = "BAD_REQUEST"


class ValidationFailed(AppError):
    """Ошибки заполнения полей: extra['fields'] = {поле: сообщение}."""
    status = 422
    default_code = "VALIDATION"


class Unauthorized(AppError):
    status = 401
    default_code = "UNAUTHORIZED"


class Forbidden(AppError):
    status = 403
    default_code = "FORBIDDEN"


class NotFound(AppError):
    status = 404
    default_code = "NOT_FOUND"


class Conflict(AppError):
    status = 409
    default_code = "CONFLICT"
