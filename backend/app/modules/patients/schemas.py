from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from .models import Patient


class PatientIn(BaseModel):
    iin: str = ""
    last_name: str = ""
    first_name: str = ""
    middle_name: str | None = None
    birth_date: date | None = None
    sex: str | None = None
    mobile_phone: str = ""
    address: str | None = None
    doc_type: str | None = None
    doc_no: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("birth_date", mode="before")
    @classmethod
    def _empty_date(cls, v):
        return None if v in ("", None) else v


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    iin: str
    last_name: str
    first_name: str
    middle_name: str | None
    fio: str
    birth_date: date
    sex: str | None
    mobile_phone: str
    address: str | None
    doc_type: str | None
    doc_no: str | None
    reg_date: date | None


def patient_out(p: Patient) -> PatientOut:
    return PatientOut.model_validate(p)
