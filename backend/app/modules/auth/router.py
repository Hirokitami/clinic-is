from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import Unauthorized
from app.core.security import create_token, verify_password

from .dependencies import current_user
from .models import UserAccount
from .schemas import LoginIn, UserOut, user_out

router = APIRouter(prefix="/api/auth", tags=["Доступ и безопасность"])


@router.post("/login", response_model=UserOut, summary="Вход в систему (функция 1)")
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    u = db.get(UserAccount, data.login.strip())
    if not u or not u.is_active or not verify_password(data.password, u.password_hash):
        raise Unauthorized("Неверный логин или пароль", code="BAD_CREDENTIALS")
    response.set_cookie(settings.cookie_name, create_token(u.login), httponly=True, samesite="lax",
                        secure=settings.cookie_secure, max_age=settings.token_minutes * 60, path="/")
    return user_out(u)


@router.post("/logout", summary="Выход")
def logout(response: Response):
    response.delete_cookie(settings.cookie_name, path="/")
    return {"message": "Выход выполнен"}


@router.get("/me", response_model=UserOut, summary="Текущий пользователь")
def me(user: UserAccount = Depends(current_user)):
    return user_out(user)
