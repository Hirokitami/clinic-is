from pydantic import BaseModel, ConfigDict


class RefItem(BaseModel):
    code: str
    name: str
    extra: dict = {}


class SpecialtyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    specialty_code: str
    name: str
    visit_minutes: int
