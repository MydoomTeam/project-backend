import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.domain.constants import SYSTEM_ADMIN_ID
from app.repositories.alert_repository import AlertRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.models.match import MatchModel

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS = 30


def _record_overdue_alert(db, alert_repo, audit_repo, match) -> None:
    message = f"Partido #{match.id} vencido. Estado actual: {match.status}."
    try:
        alert = alert_repo.create(event_type="match_overdue", message=message)
        audit_repo.log_action(
            actor_id=SYSTEM_ADMIN_ID,
            action="CREATE_ALERTA",
            change_description=f"scheduler:Alert:{alert.id}",
        )
    except Exception as e:
        logger.error(f"Error registrando alerta para match {match.id}: {e}")
        audit_repo.log_action(
            actor_id=SYSTEM_ADMIN_ID,
            action="CREATE_ALERTA_FAILED",
            change_description=f"scheduler:Enfrentamiento:{match.id}",
        )
        db.rollback()


def check_overdue_events():
    db = SessionLocal()
    try:
        today = date.today()
        audit_repo = AuditLogRepository(db)

        overdue_matches = db.query(MatchModel).filter(
            MatchModel.scheduled_datetime.isnot(None),
            MatchModel.status.in_(["Programado", "En curso"]),
            MatchModel.scheduled_datetime <= today,
        ).all()

        if not overdue_matches:
            audit_repo.log_action(
                actor_id=SYSTEM_ADMIN_ID,
                action="CHECK_OVERDUE_OK",
                change_description="scheduler:Enfrentamiento",
            )
            return

        alert_repo = AlertRepository(db)
        for match in overdue_matches:
            _record_overdue_alert(db, alert_repo, audit_repo, match)

    except Exception as e:
        logger.error(f"Scheduler error at check_overdue_events: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_overdue_events,
        trigger=IntervalTrigger(seconds=_CHECK_INTERVAL_SECONDS),
        id="check_overdue_events_job",
        name="Revisar eventos vencidos para alertas",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler iniciado. Revisando eventos cada {_CHECK_INTERVAL_SECONDS} segundos.")
