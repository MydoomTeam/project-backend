import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_PATTERN_USERNAME = r"^[A-Za-z0-9]+$"
_PATTERN_PASSWORD = r"^[A-Za-z0-9!@#$%^&*()\-_+=\[\]{};:.,<>/?]+$"
_PATTERN_IDENTIFIER = r"^[A-Za-z0-9!@#$%^&*()\-_+=\[\]{};:.,<>/?@]+$"


class PasswordUpdate(BaseModel):
    password: str
    password_confirm: str


class JugadorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_usuario: str
    correo_electronico: str
    rol: str
    fecha_ultimo_acceso: date
    elo_global: int


class UsuarioRegistro(BaseModel):
    nombre_usuario: str = Field(min_length=3, max_length=30)
    correo_electronico: EmailStr
    contrasena: str = Field(min_length=8)

    @field_validator("nombre_usuario")
    @classmethod
    def validar_nombre(cls, value):
        if not re.match(_PATTERN_USERNAME, value):
            raise ValueError("El nombre de usuario solo permite letras y números")
        return value

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena(cls, value):
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
    identificador: str
    contrasena: str

    @field_validator("identificador")
    @classmethod
    def validar_identificador(cls, value):
        if not re.match(_PATTERN_IDENTIFIER, value):
            raise ValueError("Caracteres inválidos en el identificador")
        return value

    @field_validator("contrasena")
    @classmethod
    def validar_contrasena_login(cls, value):
        if not re.match(_PATTERN_PASSWORD, value):
            raise ValueError("Caracteres inválidos en la contraseña")
        return value


class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    jugador: JugadorRead
