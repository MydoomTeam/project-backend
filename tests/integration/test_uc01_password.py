from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.domain.models.player import Player
from app.domain.schemas.player import PasswordUpdate
from app.models.audit_log import AuditLogModel
from app.repositories.player_repository import PlayerRepository
from app.services.player_service import PlayerService


def _password_update(password="Password123", confirm="Password123") -> PasswordUpdate:
    return PasswordUpdate(password=password, password_confirm=confirm)


def test_admin_password_valid(client, db_session):
    response = client.post(
        "/admins/password",
        json={"password": "Password123", "password_confirm": "Password123"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "password_updated"}

    # El actor proviene de get_current_user (jugador autenticado = 1), no del stub.
    player = db_session.query(Player).filter_by(id=1).first()
    assert player.password_hash.startswith("$2")
    audit = (
        db_session.query(AuditLogModel)
        .filter_by(action="UPDATE_PASSWORD")
        .one()
    )
    assert audit.user_id == 1


def test_admin_password_and_confirmation_differ(client, db_session):
    response = client.post(
        "/admins/password",
        json={"password": "Password123", "password_confirm": "Different123"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_error"


def test_admin_password_weak(client, db_session):
    response = client.post(
        "/admins/password",
        json={"password": "Pwd1", "password_confirm": "Pwd1"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["details"]

    response = client.post(
        "/admins/password",
        json={"password": "password123", "password_confirm": "password123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["details"]


def test_admin_password_db_failure(client, db_session):
    with patch.object(PlayerRepository, "update_password", side_effect=Exception("db error")):
        response = client.post(
            "/admins/password",
            json={"password": "Password123", "password_confirm": "Password123"},
        )

    assert response.status_code == 500
    assert (
        db_session.query(AuditLogModel)
        .filter_by(action="UPDATE_PASSWORD_FAILED")
        .count()
        == 1
    )


def test_change_password_nonexistent_actor(db_session):
    service = PlayerService(db_session)

    with pytest.raises(HTTPException) as ctx:
        service.change_password(9999, _password_update())

    assert ctx.value.status_code == 404
