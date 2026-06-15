from dataclasses import dataclass

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.services.player_service import PlayerService, RegistrationOutcome

CLIENT = TestClient(app)
REGISTER_URL = "/users"
LOGIN_URL = "/sessions"


@dataclass
class DummyPlayer:
    id: int = 1
    username: str = "alex123"
    email: str = "alex@test.com"
    role: str = "JUGADOR"
    global_elo: int = 0
    last_access_date: str = "2026-01-01"


def build_registration_payload(
    username: str = "alex123",
    email: str = "alex@test.com",
    password: str = "Password123!",
    ) -> dict:
    return {
        "username": username,
        "email": email,
        "password": password,
    }


def build_login_payload(
    identifier: str = "alex123",
    password: str = "Password123!",
) -> dict:
    return {"identifier": identifier, "password": password}


def register(payload: dict):
    return CLIENT.post(REGISTER_URL, json=payload)


def login(payload: dict):
    return CLIENT.post(LOGIN_URL, json=payload)


def test_register_success(monkeypatch):
    def fake_register_user(self, payload):
        return RegistrationOutcome(player=DummyPlayer())

    monkeypatch.setattr(PlayerService, "register_user", fake_register_user)

    response = register(build_registration_payload())

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    "payload,duplicated_user,duplicated_email",
    [
        (build_registration_payload(email="otro@test.com"), True, False),
        (build_registration_payload(username="otro"), False, True),
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

    response = login(build_login_payload(password="incorrecta"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "url,payload",
    [
        (REGISTER_URL, build_registration_payload(username="ab")),
        (REGISTER_URL, build_registration_payload(password="123")),
        (REGISTER_URL, build_registration_payload(username="alexñ")),
        (REGISTER_URL, build_registration_payload(password="Pass\U0001f642123")),
        (LOGIN_URL, {"identifier": "alex€", "password": "Password123!"}),
        (LOGIN_URL, {"identifier": "alex123"}),
        (REGISTER_URL, {"email": "alex@test.com", "password": "Password123!"}),
    ],
)
def test_input_validation_rejects_invalid_payloads(url, payload):
    response = CLIENT.post(url, json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
