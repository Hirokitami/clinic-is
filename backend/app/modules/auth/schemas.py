from pydantic import BaseModel

from .dependencies import ROLE_NAMES
from .models import UserAccount


class LoginIn(BaseModel):
    login: str
    password: str


class UserOut(BaseModel):
    login: str
    role_code: str
    role_name: str
    display_name: str
    tab_no: str | None = None
    iin: str | None = None


def user_out(u: UserAccount) -> UserOut:
    return UserOut(login=u.login, role_code=u.role_code, role_name=ROLE_NAMES.get(u.role_code, u.role_code),
                   display_name=u.display_name, tab_no=u.tab_no, iin=u.iin)
