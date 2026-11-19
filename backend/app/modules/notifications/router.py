from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.dependencies import require_roles

from .models import SmsOutbox
from .schemas import SmsOut

router = APIRouter(prefix="/api/sms", tags=["Уведомления"], dependencies=[Depends(require_roles("OPERATOR", "ADMIN"))])


@router.get("", response_model=list[SmsOut], summary="Журнал SMS-подтверждений (Т8)")
def sms_log(limit: int = 100, db: Session = Depends(get_db)):
    return db.scalars(select(SmsOutbox).order_by(SmsOutbox.id.desc()).limit(min(limit, 500))).all()
