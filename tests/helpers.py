from datetime import date, timedelta

from app.domain.models.admin import Administrador
from app.domain.models.enfrentamiento import Enfrentamiento
from app.domain.models.inscripcion import Inscripcion
from app.domain.models.jugador import Jugador
from app.domain.models.ronda import Ronda
from app.domain.models.torneo import Torneo


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


def _jugador(jugador_id: int, nombre: str, correo: str, today: date) -> Jugador:
    return Jugador(
        id=jugador_id,
        nombre_usuario=nombre,
        correo_electronico=correo,
        contrasena_hash="hash",
        rol="jugador",
        fecha_ultimo_acceso=today,
        elo_global=1000,
    )


def _inscripcion(inscripcion_id: int, jugador_id: int, today: date) -> Inscripcion:
    return Inscripcion(
        id=inscripcion_id,
        torneo_id=1,
        jugador_id=jugador_id,
        estado_participante="Activo",
        fecha_inscripcion=today,
    )


def seed_overdue_enfrentamiento(session) -> Enfrentamiento:
    today = date.today()
    past = today - timedelta(days=1)

    seed_admin(session)

    session.add(
        Torneo(
            id=1,
            administrador_id=1,
            nombre="Torneo Test",
            tipo_eliminacion="simple",
            nombre_juego="General",
            categoria_juego="General",
            numero_participantes=8,
            numero_rondas=1,
            duracion_ronda=30,
            estado="Activo",
            fecha_inicio=today,
        )
    )
    session.add(Ronda(id=1, torneo_id=1, numero_fase=1))
    session.add(_jugador(1, "jugador1", "j1@test.com", today))
    session.add(_jugador(2, "jugador2", "j2@test.com", today))
    session.add(_inscripcion(1, 1, today))
    session.add(_inscripcion(2, 2, today))
    enfrentamiento = Enfrentamiento(
        id=1,
        ronda_id=1,
        inscripcion_a_id=1,
        inscripcion_b_id=2,
        estado_match="Pendiente",
        marcador_detalle="0-0",
        fecha_hora_programada=past,
    )
    session.add(enfrentamiento)
    session.commit()
    return enfrentamiento
