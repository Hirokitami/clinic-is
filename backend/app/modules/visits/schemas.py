from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.appointments.schemas import AppointmentOut
from app.modules.lab.schemas import ReferralIn, ReferralOut, TestResultOut
from app.modules.patients.schemas import PatientOut
from app.modules.procedures.schemas import PrescriptionIn, PrescriptionOut
from app.modules.schedule.schemas import SlotOut

from .models import RenderedService


class ServiceLineIn(BaseModel):
    service_code: str
    qty: int = Field(default=1, ge=1, le=50)


class VisitIn(BaseModel):
    complaints: str = ""
    icd_code: str = ""
    conclusion: str | None = None
    prescriptions: list[PrescriptionIn] = []
    referrals: list[ReferralIn] = []
    services: list[ServiceLineIn] = []


class VisitEditIn(BaseModel):
    complaints: str = ""
    icd_code: str = ""
    conclusion: str | None = None


class ServiceLineOut(BaseModel):
    line_no: str
    service_code: str
    service_name: str
    qty: int
    price_kzt: float
    amount_kzt: float


def service_line_out(s: RenderedService) -> ServiceLineOut:
    price = float(s.price_kzt)
    return ServiceLineOut(line_no=s.line_no, service_code=s.service_code, service_name=s.service.name,
                          qty=s.qty, price_kzt=price, amount_kzt=price * s.qty)


class VisitChangeOut(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime
    changed_by: str


class VisitOut(BaseModel):
    visit_no: str
    appt_no: str
    date: date
    complaints: str
    icd_code: str
    diagnosis_name: str
    conclusion: str | None
    finished_at: datetime
    author: str
    doctor_name: str
    specialty_name: str
    tab_no: str
    prescriptions: list[PrescriptionOut] = []
    referrals: list[ReferralOut] = []
    services: list[ServiceLineOut] = []
    services_total: float = 0
    changes: list[VisitChangeOut] = []


class PatientHistoryOut(BaseModel):
    patient: PatientOut
    visits: list[VisitOut]
    prescriptions: list[PrescriptionOut]
    referrals: list[ReferralOut]
    tests: list[TestResultOut]


class DoctorDayRow(BaseModel):
    slot: SlotOut
    appointment: AppointmentOut | None
    visit_no: str | None = None
