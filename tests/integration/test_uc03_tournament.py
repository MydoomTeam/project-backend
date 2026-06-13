from datetime import date
from unittest.mock import patch

from app.domain.models.player import Player
from app.models.tournament import TournamentModel
from app.repositories.tournament_repository import TournamentRepository


def _seed_player(db_session, player_id: int = 1):
    if not db_session.query(Player).filter_by(id=player_id).first():
        db_session.add(Player(
            id=player_id,
            username="test_creador",
            email="creador@test.com",
            password_hash="hash",
            role="jugador",
            last_access_date=date.today(),
            global_elo=0,
        ))
        db_session.commit()


def _tournament_payload(**overrides):
    payload = {
        "name": "Copa Arena",
        "elimination_type": "Eliminación Sencilla",
        "rounds": 3,
    }
    payload.update(overrides)
    return payload


def test_create_tournament_valid(client):
    response = client.post("/tournaments", json=_tournament_payload())

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Copa Arena"
    assert data["status"] == "Pendiente"
    assert data["elimination_type"] == "Eliminación Sencilla"
    assert data["rounds"] == 3


def test_create_tournament_missing_field(client):
    payload = _tournament_payload()
    del payload["name"]

    response = client.post("/tournaments", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "validation_error"


def test_create_tournament_empty_name(client):
    response = client.post("/tournaments", json=_tournament_payload(name=""))
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "validation_error"


def test_create_tournament_invalid_rounds(client):
    response = client.post(
        "/tournaments",
        json=_tournament_payload(rounds=0),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "validation_error"


def test_create_tournament_rounds_exceed_maximum(client):
    response = client.post(
        "/tournaments",
        json=_tournament_payload(elimination_type="Eliminación Sencilla", rounds=10),
    )
    assert response.status_code == 400


def test_create_tournament_invalid_elimination_type(client):
    response = client.post(
        "/tournaments",
        json=_tournament_payload(elimination_type="invalido"),
    )

    assert response.status_code == 400


def test_create_tournament_db_failure(client):
    with patch.object(TournamentRepository, "save", side_effect=Exception("db error")):
        response = client.post("/tournaments", json=_tournament_payload())

    assert response.status_code == 500


def test_get_tournament_by_id(client, db_session):
    _seed_player(db_session)
    created = client.post("/tournaments", json=_tournament_payload()).json()

    response = client.get(f"/tournaments/{created['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["name"] == "Copa Arena"
    assert data["status"] == "Pendiente"
    assert data["total_participants"] == 0


def test_get_tournament_not_found(client):
    response = client.get("/tournaments/9999")
    assert response.status_code == 404
