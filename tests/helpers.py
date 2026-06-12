from datetime import date, timedelta

from app.domain.models.admin import Administrador
from app.domain.models.scheduled_match import ScheduledMatch


def seed_admin(session, admin_id: int = 1) -> Administrador:
    admin = session.query(Administrador).filter_by(id=admin_id).first()
    if admin:
        return admin

    admin = Administrador(
        id=admin_id,
        nombre_usuario="admin_test",
        correo_electronico="admin@test.com",
        contrasena_hash="hash",
        rol="administrador",
        fecha_ultimo_acceso=date.today(),
    )
    session.add(admin)
    session.flush()
    return admin


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
