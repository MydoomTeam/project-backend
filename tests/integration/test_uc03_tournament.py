from datetime import date
from unittest.mock import patch

from app.domain.models.player import Player
from app.domain.models.elo_history import EloHistory
from app.models.audit_log import AuditLogModel
from app.models.match import MatchModel
from app.models.registration import RegistrationModel
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


def test_create_tournament_writes_audit_log(client, db_session):
    response = client.post("/tournaments", json=_tournament_payload())

    assert response.status_code == 201
    created_id = response.json()["id"]

    audit = (
        db_session.query(AuditLogModel)
        .filter_by(action="CREAR_TORNEO")
        .order_by(AuditLogModel.id.desc())
        .first()
    )

    assert audit is not None
    assert audit.user_id == 1
    assert audit.change_description == f"tournament_id={created_id}"


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


def test_record_result_updates_match_elo_and_audit(client, db_session):
    player_one = db_session.query(Player).filter_by(id=1).one()
    player_one.username = "admin_player"
    player_one.email = "admin_player@test.com"
    player_one.password_hash = "hash"
    player_one.role = "jugador"
    player_one.last_access_date = date.today()
    player_one.global_elo = 1200

    player_two = Player(
        id=2,
        username="rival_player",
        email="rival_player@test.com",
        password_hash="hash",
        role="jugador",
        last_access_date=date.today(),
        global_elo=1200,
    )
    db_session.add(player_two)
    db_session.flush()

    tournament = TournamentModel(
        name="Copa Resultado",
        elimination_type="Eliminación Sencilla",
        rounds=1,
        status="En curso",
        creator_id=1,
    )
    db_session.add(tournament)
    db_session.flush()

    match = MatchModel(
        tournament_id=tournament.id,
        round=1,
        position=0,
        bracket_type="ganadores",
        player1_id=1,
        player2_id=2,
        status="En curso",
    )
    db_session.add(match)
    db_session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/matches/{match.id}/result",
        json={"winner_id": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["match"]["winner_id"] == 1
    assert body["match"]["status"] == "Finalizado"
    assert body["tournament_finished"] is True
    assert body["winner_new_elo"] > 1200
    assert body["loser_new_elo"] < 1200

    db_session.refresh(match)
    db_session.refresh(tournament)
    assert match.winner_id == 1
    assert match.status == "Finalizado"
    assert tournament.status == "Finalizado"

    elo_rows = (
        db_session.query(EloHistory)
        .filter_by(match_id=match.id)
        .order_by(EloHistory.player_id.asc())
        .all()
    )
    assert len(elo_rows) == 2
    assert {row.player_id for row in elo_rows} == {1, 2}

    audit = (
        db_session.query(AuditLogModel)
        .filter_by(action="REGISTRAR_RESULTADO")
        .order_by(AuditLogModel.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.user_id == 1
    assert f"match_id={match.id}" in (audit.change_description or "")


def test_record_result_advances_winner_to_next_match(client, db_session):
    player_one = db_session.query(Player).filter_by(id=1).one()
    player_one.username = "admin_player"
    player_one.email = "admin_player_flow@test.com"
    player_one.password_hash = "hash"
    player_one.role = "jugador"
    player_one.last_access_date = date.today()
    player_one.global_elo = 1200

    player_two = Player(
        id=2,
        username="rival_player",
        email="rival_player_flow@test.com",
        password_hash="hash",
        role="jugador",
        last_access_date=date.today(),
        global_elo=1150,
    )
    db_session.add(player_two)
    db_session.flush()

    tournament = TournamentModel(
        name="Copa Avance",
        elimination_type="Eliminación Sencilla",
        rounds=2,
        status="En curso",
        creator_id=1,
    )
    db_session.add(tournament)
    db_session.flush()

    current_match = MatchModel(
        tournament_id=tournament.id,
        round=1,
        position=0,
        bracket_type="ganadores",
        player1_id=1,
        player2_id=2,
        status="En curso",
    )
    next_match = MatchModel(
        tournament_id=tournament.id,
        round=2,
        position=0,
        bracket_type="ganadores",
        player1_id=None,
        player2_id=None,
        status="Pendiente",
    )
    db_session.add_all([current_match, next_match])
    db_session.commit()

    response = client.post(
        f"/tournaments/{tournament.id}/matches/{current_match.id}/result",
        json={"winner_id": 1},
    )

    assert response.status_code == 200
    assert response.json()["tournament_finished"] is False

    db_session.refresh(current_match)
    db_session.refresh(next_match)
    assert current_match.winner_id == 1
    assert next_match.player1_id == 1
    assert next_match.status == "Pendiente"


def test_generate_bracket_with_confirmed_players_creates_matches_and_audit(client, db_session):
    creator = db_session.query(Player).filter_by(id=1).one()
    creator.username = "admin_bracket"
    creator.email = "admin_bracket@test.com"
    creator.password_hash = "hash"
    creator.role = "jugador"
    creator.last_access_date = date.today()
    creator.global_elo = 1500

    player_two = Player(
        id=2,
        username="alpha_seed",
        email="alpha_seed@test.com",
        password_hash="hash",
        role="jugador",
        last_access_date=date.today(),
        global_elo=1400,
    )
    player_three = Player(
        id=3,
        username="beta_seed",
        email="beta_seed@test.com",
        password_hash="hash",
        role="jugador",
        last_access_date=date.today(),
        global_elo=1300,
    )
    db_session.add_all([player_two, player_three])
    db_session.flush()

    tournament = TournamentModel(
        name="Copa Llaves",
        elimination_type="Eliminación Sencilla",
        rounds=2,
        status="Pendiente",
        creator_id=1,
    )
    db_session.add(tournament)
    db_session.flush()

    db_session.add_all([
        RegistrationModel(tournament_id=tournament.id, player_id=1, status="Confirmado"),
        RegistrationModel(tournament_id=tournament.id, player_id=2, status="Confirmado"),
        RegistrationModel(tournament_id=tournament.id, player_id=3, status="Confirmado"),
    ])
    db_session.commit()

    response = client.post(f"/tournaments/{tournament.id}/bracket")

    assert response.status_code == 201
    body = response.json()
    assert body["tournament_id"] == tournament.id
    assert body["tournament_status"] == "Listo para iniciar"
    assert len(body["matches"]) >= 2

    db_session.refresh(tournament)
    assert tournament.status == "Listo para iniciar"
    assert db_session.query(MatchModel).filter_by(tournament_id=tournament.id).count() >= 2

    audit = (
        db_session.query(AuditLogModel)
        .filter_by(action="GENERAR_BRACKET")
        .order_by(AuditLogModel.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.user_id == 1
    assert f"tournament_id={tournament.id}" in (audit.change_description or "")
