from dataclasses import dataclass

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.player_service import PlayerService, RegistrationOutcome


CLIENT = TestClient(app)
REGISTER_URL = "/usuarios/registrar"
LOGIN_URL = "/usuarios/login"


@dataclass
class DummyPlayer:
    id: int = 1
    nombre_usuario: str = "alex123"
    correo_electronico: str = "alex@test.com"
    rol: str = "JUGADOR"
    elo_global: int = 0
    fecha_ultimo_acceso: str = "2026-01-01"


def build_registration_payload(
    nombre_usuario: str = "alex123",
    correo_electronico: str = "alex@test.com",
    contrasena: str = "Password123!",
    ) -> dict:
    return {
        "nombre_usuario": nombre_usuario,
        "correo_electronico": correo_electronico,
        "contrasena": contrasena,
    }


def build_login_payload(
    identificador: str = "alex123",
    contrasena: str = "Password123!",
) -> dict:
    return {"identificador": identificador, "contrasena": contrasena}


def register(payload: dict):
    return CLIENT.post(REGISTER_URL, json=payload)


def login(payload: dict):
    return CLIENT.post(LOGIN_URL, json=payload)


def test_register_success(monkeypatch):
    def fake_register_user(self, payload):
        return RegistrationOutcome(jugador=DummyPlayer())

    monkeypatch.setattr(PlayerService, "register_user", fake_register_user)

    response = register(build_registration_payload())

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    "payload,duplicated_user,duplicated_email",
    [
        (build_registration_payload(correo_electronico="otro@test.com"), True, False),
        (build_registration_payload(nombre_usuario="otro"), False, True),
    ],
)
def test_register_duplicate(monkeypatch, payload, duplicated_user, duplicated_email):
    def fake_register_user(self, payload):
        return RegistrationOutcome(
            duplicate_username=duplicated_user,
            duplicate_email=duplicated_email,
        )

    monkeypatch.setattr(PlayerService, "register_user", fake_register_user)

    response = register(payload)

    assert response.status_code == status.HTTP_409_CONFLICT


def test_login_success(monkeypatch):
    def fake_login(self, payload):
        return DummyPlayer()

    monkeypatch.setattr(PlayerService, "login", fake_login)

    response = login(build_login_payload())

    assert response.status_code == status.HTTP_200_OK


def test_login_wrong_password(monkeypatch):
    def fake_login(self, payload):
        return None

    monkeypatch.setattr(PlayerService, "login", fake_login)

    response = login(build_login_payload(contrasena="incorrecta"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "url,payload",
    [
        (REGISTER_URL, build_registration_payload(nombre_usuario="ab")),
        (REGISTER_URL, build_registration_payload(contrasena="123")),
        (REGISTER_URL, build_registration_payload(nombre_usuario="alexñ")),
        (REGISTER_URL, build_registration_payload(contrasena="Pass\U0001f642123")),
        (LOGIN_URL, {"identificador": "alex€", "contrasena": "Password123!"}),
        (LOGIN_URL, {"identificador": "alex123"}),
        (REGISTER_URL, {"correo_electronico": "alex@test.com", "contrasena": "Password123!"}),
    ],
)
def test_input_validation_rejects_invalid_payloads(url, payload):
    response = CLIENT.post(url, json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
