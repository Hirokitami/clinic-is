from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth.dependencies import require_roles
from app.modules.auth.models import UserAccount

from . import service
from .schemas import ReferralOut, TestResultIn, TestResultOut, referral_out, test_result_out

router = APIRouter(prefix="/api/lab", tags=["Лаборатория"])
lab = require_roles("LAB")


@router.get("/referrals", response_model=list[ReferralOut], summary="Направления на исследования")
def referrals(status: str | None = "ORDERED", db: Session = Depends(get_db), _: UserAccount = Depends(lab)):
    return [referral_out(r) for r in service.list_referrals(db, status)]


@router.post("/referrals/{ref_no}/result", response_model=TestResultOut, status_code=201,
             summary="Внесение результата исследования по направлению")
def add_result(ref_no: str, data: TestResultIn, db: Session = Depends(get_db), user: UserAccount = Depends(lab)):
    return test_result_out(service.record_result(db, user, ref_no, data.value_text, data.done_date))
