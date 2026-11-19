"""Рабочее место медицинской сестры."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import clock
from app.core.db import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.auth.models import UserAccount

from . import service
from .schemas import ExecuteIn, NurseRow

router = APIRouter(prefix="/api/nurse", tags=["Процедуры"])
nurse = require_roles("NURSE")


@router.get("/procedures", response_model=list[NurseRow], summary="Перечень процедур на дату (функция 20)")
def procedures(on: date | None = None, cabinet: str | None = None, state: str | None = None,
               db: Session = Depends(get_db), _: UserAccount = Depends(nurse)):
    return service.procedures_for_day(db, on or clock.today(), cabinet, state)


@router.post("/prescriptions/{rx_no}/execute", summary="Отметка выполнения процедуры (функция 21)")
def execute(rx_no: str, data: ExecuteIn, db: Session = Depends(get_db), user: UserAccount = Depends(nurse)):
    done, total = service.execute(db, user, rx_no, data.note)
    return {"message": f"Выполнение процедуры отмечено (сеанс {done} из {total})", "done_count": done,
            "sessions": total}
