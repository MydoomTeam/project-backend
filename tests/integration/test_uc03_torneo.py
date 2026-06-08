from unittest.mock import patch

from app.domain.models.log_auditoria import LogAuditoria
from app.domain.models.torneo import Torneo
from app.repositories.torneo_repository import TorneoRepository


def _torneo_payload(**overrides):
    payload = {
        "nombre": "Copa Arena",
        "tipo_eliminacion": "simple",
        "duracion_ronda_min": 45,
        "participantes_max": 16,
    }
    payload.update(overrides)
    return payload


def test_crear_torneo_valido(client, db_session):
    response = client.post("/api/tournaments", json=_torneo_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Copa Arena"
    assert data["estado"] == "Pendiente"
    assert data["opciones_siguientes"] == ["agregar_participantes", "generar_bracket"]
    assert (
        db_session.query(LogAuditoria).filter_by(accion="CREATE_TORNEO").count() == 1
    )


def test_crear_torneo_campo_faltante(client):
    payload = _torneo_payload()
    del payload["nombre"]

    response = client.post("/api/tournaments", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_error"


def test_crear_torneo_nombre_vacio(client):
    response = client.post("/api/tournaments", json=_torneo_payload(nombre=""))
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_error"


def test_crear_torneo_participantes_invalidos(client):
    response = client.post(
        "/api/tournaments",
        json=_torneo_payload(participantes_max=1),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_error"


def test_crear_torneo_duracion_invalida(client):
    response = client.post(
        "/api/tournaments",
        json=_torneo_payload(duracion_ronda_min=0),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_error"


def test_crear_torneo_tipo_eliminacion_invalido(client):
    response = client.post(
        "/api/tournaments",
        json=_torneo_payload(tipo_eliminacion="invalido"),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "validation_error"


def test_crear_torneo_fallo_bd(client, db_session):
    with patch.object(TorneoRepository, "create", side_effect=Exception("db error")):
        response = client.post("/api/tournaments", json=_torneo_payload())

    assert response.status_code == 500
    assert db_session.query(Torneo).count() == 0
    assert (
        db_session.query(LogAuditoria)
        .filter_by(accion="CREATE_TORNEO_FAILED")
        .count()
        == 1
    )


def test_get_torneo_por_id(client):
    created = client.post("/api/tournaments", json=_torneo_payload()).json()

    response = client.get(f"/api/tournaments/{created['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["nombre"] == "Copa Arena"
    assert data["estado"] == "Pendiente"
    assert data["metadata"]["participantes_max"] == 16


def test_get_torneo_no_existe(client):
    response = client.get("/api/tournaments/9999")
    assert response.status_code == 404
