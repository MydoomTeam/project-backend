from datetime import date
from unittest.mock import patch

from app.domain.models.jugador import Jugador
from app.models.tournament import TournamentModel
from app.repositories.tournament_repository import TournamentRepository


def _seed_jugador(db_session, jugador_id: int = 1):
    if not db_session.query(Jugador).filter_by(id=jugador_id).first():
        db_session.add(Jugador(
            id=jugador_id,
            nombre_usuario="test_creador",
            correo_electronico="creador@test.com",
            contrasena_hash="hash",
            rol="jugador",
            fecha_ultimo_acceso=date.today(),
            elo_global=0,
        ))
        db_session.commit()


def _torneo_payload(**overrides):
    payload = {
        "nombre": "Copa Arena",
        "tipo_eliminacion": "Eliminación Sencilla",
        "rondas": 3,
    }
    payload.update(overrides)
    return payload


def test_crear_torneo_valido(client):
    response = client.post("/tournaments", json=_torneo_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["nombre"] == "Copa Arena"
    assert data["estado"] == "Pendiente"
    assert data["tipo_eliminacion"] == "Eliminación Sencilla"
    assert data["rondas"] == 3


def test_crear_torneo_campo_faltante(client):
    payload = _torneo_payload()
    del payload["nombre"]

    response = client.post("/tournaments", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "validation_error"


def test_crear_torneo_nombre_vacio(client):
    response = client.post("/tournaments", json=_torneo_payload(nombre=""))
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "validation_error"


def test_crear_torneo_rondas_invalidas(client):
    response = client.post(
        "/tournaments",
        json=_torneo_payload(rondas=0),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "validation_error"


def test_crear_torneo_rondas_exceden_maximo(client):
    response = client.post(
        "/tournaments",
        json=_torneo_payload(tipo_eliminacion="Eliminación Sencilla", rondas=10),
    )
    assert response.status_code == 400


def test_crear_torneo_tipo_eliminacion_invalido(client):
    response = client.post(
        "/tournaments",
        json=_torneo_payload(tipo_eliminacion="invalido"),
    )

    assert response.status_code == 400


def test_crear_torneo_fallo_bd(client):
    with patch.object(TournamentRepository, "guardar_con_auditoria", side_effect=Exception("db error")):
        response = client.post("/tournaments", json=_torneo_payload())

    assert response.status_code == 500


def test_get_torneo_por_id(client, db_session):
    _seed_jugador(db_session)
    created = client.post("/tournaments", json=_torneo_payload()).json()

    response = client.get(f"/tournaments/{created['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["nombre"] == "Copa Arena"
    assert data["estado"] == "Pendiente"
    assert data["total_participantes"] == 0


def test_get_torneo_no_existe(client):
    response = client.get("/tournaments/9999")
    assert response.status_code == 404
