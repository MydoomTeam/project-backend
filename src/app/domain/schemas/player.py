import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_PATTERN_USERNAME = r"^[A-Za-z0-9]+$"
_PATTERN_PASSWORD = r"^[A-Za-z0-9!@#$%^&*()\-_+=\[\]{};:.,<>/?]+$"
_PATTERN_IDENTIFIER = r"^[A-Za-z0-9!@#$%^&*()\-_+=\[\]{};:.,<>/?@]+$"


class PasswordUpdate(BaseModel):
    password: str
    password_confirm: str


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    last_access_date: date
    global_elo: int


class PlayerTournamentHistoryItem(BaseModel):
    id: int
    name: str
    elimination_type: str
    rounds: int
    status: str
    is_creator: bool
    registration_status: str | None


class EloHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    player_id: int
    previous_elo: int
    current_elo: int
    change_date: date


class UserRegistration(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("username")
    @classmethod
    def validate_name(cls, value):
        if not re.match(_PATTERN_USERNAME, value):
            raise ValueError("El nombre de usuario solo permite letras y números")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if not re.match(_PATTERN_PASSWORD, value):
            raise ValueError("La contraseña contiene caracteres no permitidos")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("La contraseña debe contener al menos una letra")
        if not re.search(r"[0-9]", value):
            raise ValueError("La contraseña debe contener al menos un número")
        if not re.search(r"[!@#$%^&()\-_+=\[\]{};:.,<>/?]", value):
            raise ValueError("La contraseña debe contener al menos un símbolo especial")
        return value


class LoginRequest(BaseModel):
    identifier: str
    password: str

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value):
        if not re.match(_PATTERN_IDENTIFIER, value):
            raise ValueError("Caracteres inválidos en el identificador")
        return value

    @field_validator("password")
    @classmethod
    def validate_login_password(cls, value):
        if not re.match(_PATTERN_PASSWORD, value):
            raise ValueError("Caracteres inválidos en la contraseña")
        return value


class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    player: PlayerRead
