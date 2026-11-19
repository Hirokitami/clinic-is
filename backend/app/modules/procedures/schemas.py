from datetime import date, datetime

from pydantic import BaseModel, Field

from .models import Prescription


class PrescriptionIn(BaseModel):
    procedure_code: str
    sessions: int = Field(ge=1, le=30)
    instructions: str | None = None


class ExecutionOut(BaseModel):
    executed_at: datetime
    nurse_login: str
    note: str | None


class PrescriptionOut(BaseModel):
    rx_no: str
    visit_no: str
    procedure_code: str
    procedure_name: str
    cabinet_no: str | None
    sessions: int
    done_count: int
    instructions: str | None
    start_date: date
    created_at: datetime
    author: str
    executions: list[ExecutionOut]


def prescription_out(r: Prescription) -> PrescriptionOut:
    return PrescriptionOut(
        rx_no=r.rx_no, visit_no=r.visit_no, procedure_code=r.procedure_code, procedure_name=r.procedure.name,
        cabinet_no=r.procedure.cabinet_no, sessions=r.sessions, done_count=len(r.executions),
        instructions=r.instructions, start_date=r.start_date, created_at=r.created_at, author=r.author,
        executions=[ExecutionOut(executed_at=e.executed_at, nurse_login=e.nurse_login, note=e.note)
                    for e in r.executions])


class ExecuteIn(BaseModel):
    note: str | None = None


class NurseRow(BaseModel):
    prescription: PrescriptionOut
    patient_iin: str
    patient_fio: str
    doctor_name: str
    done_today: int
    done_before: int
    remaining: int
    state: str  # todo / done_today / completed
