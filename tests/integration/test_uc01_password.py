from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.domain.models.jugador import Jugador
from app.domain.schemas.jugador import PasswordUpdate
from app.models.audit_log import AuditLogModel
from app.repositories.jugador_repository import JugadorRepository
from app.services.jugador_service import JugadorService


def _password_update(password="Password123", confirm="Password123") -> PasswordUpdate:
    return PasswordUpdate(password=password, password_confirm=confirm)


def test_admin_password_valida(client, db_session):
    response = client.post(
        "/admins/password",
        json={"password": "Password123", "password_confirm": "Password123"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "password_updated"}

    # El actor proviene de get_current_user (jugador autenticado = 1), no del stub.
    jugador = db_session.query(Jugador).filter_by(id=1).first()
    assert jugador.contrasena_hash.startswith("$2")
    audit = (
        db_session.query(AuditLogModel)
        .filter_by(accion="UPDATE_PASSWORD")
        .one()
    )
    assert audit.usuario_id == 1


def test_admin_password_y_confirmacion_diferentes(client, db_session):
    response = client.post(
        "/admins/password",
        json={"password": "Password123", "password_confirm": "Different123"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_error"


def test_admin_password_debil(client, db_session):
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


def test_admin_password_fallo_bd(client, db_session):
    with patch.object(JugadorRepository, "update_password", side_effect=Exception("db error")):
        response = client.post(
            "/admins/password",
            json={"password": "Password123", "password_confirm": "Password123"},
        )

    assert response.status_code == 500
    assert (
        db_session.query(AuditLogModel)
        .filter_by(accion="UPDATE_PASSWORD_FAILED")
        .count()
        == 1
    )


def test_cambiar_password_actor_inexistente(db_session):
    service = JugadorService(db_session)

    with pytest.raises(HTTPException) as ctx:
        service.change_password(9999, _password_update())

    assert ctx.value.status_code == 404
