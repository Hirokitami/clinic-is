from datetime import date, datetime, timedelta

from pydantic import BaseModel

from .models import Referral, TestResult


class ReferralIn(BaseModel):
    test_code: str
    note: str | None = None


class ReferralOut(BaseModel):
    ref_no: str
    visit_no: str
    test_code: str
    test_name: str
    test_group: str
    note: str | None
    status: str
    created_at: datetime
    author: str
    patient_iin: str
    patient_fio: str
    doctor_name: str
    ready_by: date


def referral_out(r: Referral) -> ReferralOut:
    a = r.visit.appointment
    return ReferralOut(
        ref_no=r.ref_no, visit_no=r.visit_no, test_code=r.test_code, test_name=r.test_type.name,
        test_group=r.test_type.test_group, note=r.note, status=r.status, created_at=r.created_at, author=r.author,
        patient_iin=a.iin, patient_fio=a.patient.fio, doctor_name=a.slot.doctor.short_name,
        ready_by=r.created_at.date() + timedelta(days=r.test_type.ready_days))


class TestResultIn(BaseModel):
    value_text: str = ""
    done_date: date | None = None


class TestResultOut(BaseModel):
    result_no: str
    test_code: str
    test_name: str
    test_group: str
    done_date: date
    value_text: str
    referral_no: str | None


def test_result_out(t: TestResult) -> TestResultOut:
    return TestResultOut(result_no=t.result_no, test_code=t.test_code, test_name=t.test_type.name,
                         test_group=t.test_type.test_group, done_date=t.done_date, value_text=t.value_text,
                         referral_no=t.referral_no)
