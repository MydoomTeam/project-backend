import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.domain.constants import SYSTEM_ADMIN_ID
from app.domain.models.enfrentamiento import Enfrentamiento
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


def check_overdue_events():
    db = SessionLocal()
    try:
        today = date.today()
        audit_repo = AuditRepository(db)

        overdue_matches = db.query(Enfrentamiento).filter(
            Enfrentamiento.estado_match == "Pendiente",
            Enfrentamiento.fecha_hora_programada <= today,
        ).all()

        if not overdue_matches:
            audit_repo.log_action(
                administrador_id=SYSTEM_ADMIN_ID,
                accion="CHECK_OVERDUE_OK",
                descripcion_cambio="scheduler:Enfrentamiento",
            )
            return

        alerta_repo = AlertaRepository(db)

        for match in overdue_matches:
            mensaje = (
                f"Enfrentamiento {match.id} del torneo asociado a ronda "
                f"{match.ronda_id} vencido."
            )
            try:
                alerta = alerta_repo.create(
                    tipo="match_overdue",
                    mensaje=mensaje,
                )
                audit_repo.log_action(
                    administrador_id=SYSTEM_ADMIN_ID,
                    accion="CREATE_ALERTA",
                    descripcion_cambio=f"scheduler:Alerta:{alerta.id}",
                )
            except Exception as e:
                logger.error(f"Error registrando alerta para match {match.id}: {e}")
                audit_repo.log_action(
                    administrador_id=SYSTEM_ADMIN_ID,
                    accion="CREATE_ALERTA_FAILED",
                    descripcion_cambio=f"scheduler:Enfrentamiento:{match.id}",
                )
                db.rollback()

    except Exception as e:
        logger.error(f"Scheduler error at check_overdue_events: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_overdue_events,
        trigger=IntervalTrigger(seconds=30),
        id="check_overdue_events_job",
        name="Revisar eventos vencidos para alertas",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler iniciado. Revisando eventos cada 30 segundos.")
