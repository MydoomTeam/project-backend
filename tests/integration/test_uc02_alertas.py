from app.domain.models.alerta import Alerta
from app.domain.models.log_auditoria import LogAuditoria
from app.tasks.scheduler import check_overdue_events
from tests.helpers import seed_overdue_enfrentamiento


def test_scheduler_crea_alerta_para_match_vencido(db_session):
    seed_overdue_enfrentamiento(db_session)

    check_overdue_events()

    assert db_session.query(Alerta).count() == 1
    assert (
        db_session.query(LogAuditoria).filter_by(accion="CREATE_ALERTA").count() == 1
    )


def test_get_alerts_muestra_alerta_creada(client, db_session):
    seed_overdue_enfrentamiento(db_session)
    check_overdue_events()

    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["tipo"] == "match_overdue"
    assert data["items"][0]["status"] == "nueva"


def test_scheduler_no_crea_alerta_duplicada(db_session):
    seed_overdue_enfrentamiento(db_session)

    check_overdue_events()
    check_overdue_events()

    assert db_session.query(Alerta).count() == 1


def test_scheduler_sin_eventos_registra_auditoria(db_session):
    check_overdue_events()

    assert (
        db_session.query(LogAuditoria).filter_by(accion="CHECK_OVERDUE_OK").count()
        == 1
    )


def test_ack_alerta(client, db_session):
    seed_overdue_enfrentamiento(db_session)
    check_overdue_events()

    alerta_id = client.get("/api/alerts").json()["items"][0]["id"]
    response = client.patch(f"/api/alerts/{alerta_id}/ack")

    assert response.status_code == 200
    assert response.json() == {"message": "acknowledged"}
