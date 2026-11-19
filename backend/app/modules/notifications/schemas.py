from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SmsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    appt_no: str
    phone: str
    text: str
    created_at: datetime
    status: str
