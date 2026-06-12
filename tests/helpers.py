from datetime import date, timedelta

from app.domain.models.scheduled_match import ScheduledMatch


def seed_overdue_scheduled_match(session) -> ScheduledMatch:
    past = date.today() - timedelta(days=1)
    scheduled_match = ScheduledMatch(
        id=1,
        estado_match="Pendiente",
        marcador_detalle="0-0",
        fecha_hora_programada=past,
    )
    session.add(scheduled_match)
    session.commit()
    return scheduled_match
