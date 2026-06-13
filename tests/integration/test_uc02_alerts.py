from app.domain.models.alert import Alert
from app.models.audit_log import AuditLogModel
from app.tasks.scheduler import check_overdue_events
from tests.helpers import seed_overdue_scheduled_match


def test_scheduler_creates_alert_for_overdue_match(db_session):
    seed_overdue_scheduled_match(db_session)

    check_overdue_events()

    assert db_session.query(Alert).count() == 1
    assert (
        db_session.query(AuditLogModel).filter_by(accion="CREATE_ALERTA").count() == 1
    )


def test_get_alerts_shows_created_alert(client, db_session):
    seed_overdue_scheduled_match(db_session)
    check_overdue_events()

    response = client.get("/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["tipo"] == "match_overdue"
    assert data["items"][0]["status"] == "nueva"


def test_scheduler_does_not_create_duplicate_alert(db_session):
    seed_overdue_scheduled_match(db_session)

    check_overdue_events()
    check_overdue_events()

    assert db_session.query(Alert).count() == 1


def test_scheduler_without_events_logs_audit(db_session):
    check_overdue_events()

    assert (
        db_session.query(AuditLogModel).filter_by(accion="CHECK_OVERDUE_OK").count()
        == 1
    )


def test_ack_alert(client, db_session):
    seed_overdue_scheduled_match(db_session)
    check_overdue_events()

    alert_id = client.get("/alerts").json()["items"][0]["id"]
    response = client.patch(f"/alerts/{alert_id}/ack")

    assert response.status_code == 200
    assert response.json() == {"message": "acknowledged"}
