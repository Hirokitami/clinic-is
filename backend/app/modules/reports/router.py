from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.dependencies import current_user, require_roles
from app.modules.auth.models import UserAccount

from . import service

router = APIRouter(prefix="/api", tags=["Отчёты и главное окно"])


@router.get("/dashboard", summary="Показатели главного окна в пределах роли")
def dashboard(db: Session = Depends(get_db), user: UserAccount = Depends(current_user)):
    return service.dashboard(db, user)


@router.get("/reports", summary="Отчёты: загрузка врачей, неявки, обращаемость, услуги",
            dependencies=[Depends(require_roles("ADMIN"))])
def reports(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db)):
    return service.clinic_report(db, date_from, date_to)
