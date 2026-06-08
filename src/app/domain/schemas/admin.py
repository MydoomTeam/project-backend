from pydantic import BaseModel

class AdminPasswordUpdate(BaseModel):
    password: str
    password_confirm: str
