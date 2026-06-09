from datetime import date
from unittest.mock import patch

from app.domain.models.admin import Administrador
from app.domain.models.log_auditoria import LogAuditoria
from app.repositories.admin_repository import AdminRepository


def _admin(**overrides) -> Administrador:
    data = {
        "id": 1,
        "nombre_usuario": "admin_test",
        "correo_electronico": "admin@test.com",
        "contrasena_hash": "old_hash",
        "rol": "administrador",
        "fecha_ultimo_acceso": date.today(),
    }
    data.update(overrides)
    return Administrador(**data)


def test_admin_password_valida(client, db_session):
    admin = db_session.query(Administrador).filter_by(id=1).first()
    admin.contrasena_hash = "old_hash"
    db_session.commit()

    response = client.post(
        "/admins/password",
        json={"password": "Password123", "password_confirm": "Password123"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "password_updated"}

    db_session.refresh(admin)
    assert admin.contrasena_hash != "old_hash"
    assert admin.contrasena_hash != "Password123"
    assert (
        db_session.query(LogAuditoria)
        .filter_by(accion="UPDATE_PASSWORD")
        .count()
        == 1
    )


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


def test_admin_no_existe(client, db_session):
    db_session.query(Administrador).delete()
    db_session.commit()

    response = client.post(
        "/admins/password",
        json={"password": "Password123", "password_confirm": "Password123"},
    )

    assert response.status_code == 404


def test_admin_password_fallo_bd(client, db_session):
    admin = db_session.query(Administrador).filter_by(id=1).first()
    admin.contrasena_hash = "old_hash"
    db_session.commit()

    with patch.object(
        AdminRepository, "update_password", side_effect=Exception("db error")
    ):
        response = client.post(
            "/admins/password",
            json={"password": "Password123", "password_confirm": "Password123"},
        )

    assert response.status_code == 500
    db_session.refresh(admin)
    assert admin.contrasena_hash == "old_hash"
    assert (
        db_session.query(LogAuditoria)
        .filter_by(accion="UPDATE_PASSWORD_FAILED")
        .count()
        == 1
    )
