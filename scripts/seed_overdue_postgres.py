from datetime import date, timedelta
from app.core.database import SessionLocal
from app.domain.models.admin import Administrador
from app.domain.models.torneo import Torneo
from app.domain.models.ronda import Ronda
from app.domain.models.jugador import Jugador
from app.domain.models.inscripcion import Inscripcion
from app.domain.models.scheduled_match import ScheduledMatch


def _get_or_create_admin_for_seed(db, admin_id: int) -> Administrador:
    admin = db.query(Administrador).filter_by(id=admin_id).first()
    if admin:
        return admin
    
    new_admin = Administrador(
        nombre_usuario="admin_seed",
        correo_electronico="admin_seed@local",
        contrasena_hash="",
        rol="administrador",
        fecha_ultimo_acceso=date.today(),
    )
    db.add(new_admin)
    db.flush()
    return new_admin


def _create_tournament_with_single_phase(db, admin_id: int) -> tuple:
    today = date.today()
    tournament = Torneo(
        administrador_id=admin_id,
        nombre="Torneo Seed",
        tipo_eliminacion="simple",
        nombre_juego="General",
        categoria_juego="General",
        numero_participantes=8,
        numero_rondas=1,
        duracion_ronda=30,
        estado="Activo",
        fecha_inicio=today,
    )
    db.add(tournament)
    db.flush()
    
    first_phase = Ronda(torneo_id=tournament.id, numero_fase=1)
    db.add(first_phase)
    db.flush()
    
    return tournament, first_phase


def _create_test_players(db) -> tuple:
    player_one = Jugador(
        nombre_usuario="jugador1_seed",
        correo_electronico="j1_seed@test.com",
        contrasena_hash="",
        rol="jugador",
        fecha_ultimo_acceso=date.today(),
        elo_global=1000,
    )
    player_two = Jugador(
        nombre_usuario="jugador2_seed",
        correo_electronico="j2_seed@test.com",
        contrasena_hash="",
        rol="jugador",
        fecha_ultimo_acceso=date.today(),
        elo_global=1000,
    )
    db.add_all([player_one, player_two])
    db.flush()
    return player_one, player_two


def _register_players_in_tournament(db, tournament_id: int, player_one: Jugador, player_two: Jugador) -> tuple:
    today = date.today()
    registration_one = Inscripcion(
        torneo_id=tournament_id,
        jugador_id=player_one.id,
        estado_participante="Activo",
        fecha_inscripcion=today,
    )
    registration_two = Inscripcion(
        torneo_id=tournament_id,
        jugador_id=player_two.id,
        estado_participante="Activo",
        fecha_inscripcion=today,
    )
    db.add_all([registration_one, registration_two])
    db.flush()
    return registration_one, registration_two


def _create_overdue_match(db, phase_id: int, registration_one_id: int, registration_two_id: int) -> ScheduledMatch:
    yesterday = date.today() - timedelta(days=1)
    overdue_match = ScheduledMatch(
        ronda_id=phase_id,
        inscripcion_a_id=registration_one_id,
        inscripcion_b_id=registration_two_id,
        estado_match="Pendiente",
        marcador_detalle="0-0",
        fecha_hora_programada=yesterday,
    )
    db.add(overdue_match)
    db.commit()
    return overdue_match


def seed_overdue():
    db = SessionLocal()
    try:
        admin = _get_or_create_admin_for_seed(db, admin_id=1)
        tournament, first_phase = _create_tournament_with_single_phase(db, admin.id)
        player_one, player_two = _create_test_players(db)
        registration_one, registration_two = _register_players_in_tournament(
            db, tournament.id, player_one, player_two
        )
        overdue_match = _create_overdue_match(
            db, first_phase.id, registration_one.id, registration_two.id
        )
        
        print("Seeded enfrentamiento id:", overdue_match.id)
        print("Ronda id:", first_phase.id, "Torneo id:", tournament.id)
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    seed_overdue()
