import unittest
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from pydantic import ValidationError

import app.services.tournament_service as tournament_service_module
from app.models.tournament import TournamentModel
from app.schemas.tournament import TournamentCreate
from app.services.tournament_service import TournamentService


@dataclass
class DummyTournament:
    id: int = 10
    nombre: str = "Torneo Unitario"
    tipo_eliminacion: str = "Eliminación Doble"
    rondas: int = 5
    estado: str = "Pendiente"
    creador_id: int = 1


class FakeTournamentRepository:
    def __init__(self, existing_tournament: TournamentModel | None = None):
        self.existing_tournament = existing_tournament
        self.saved_tournament = None

    def get_active_by_name(self, nombre: str):
        return self.existing_tournament

    def save(self, torneo):
        self.saved_tournament = torneo
        return DummyTournament(
            id=10,
            nombre=torneo.nombre,
            tipo_eliminacion=torneo.tipo_eliminacion,
            rondas=torneo.rondas,
            estado=torneo.estado,
            creador_id=torneo.creador_id,
        )


class FakeAuditLogRepository:
    def __init__(self):
        self.recorded_action = None
        self.recorded_date = None
        self.recorded_user_id = None

    def record(self, accion, usuario_id, fecha):
        self.recorded_action = accion
        self.recorded_user_id = usuario_id
        self.recorded_date = fecha


class FixedDateTime:
    @classmethod
    def now(cls):
        return datetime(2026, 6, 7, 12, 0, 0)


def build_payload(
    nombre: str = "Torneo Unitario",
    tipo_eliminacion: str = "Eliminación Doble",
    rondas: int = 5,
) -> TournamentCreate:
    return TournamentCreate(
        nombre=nombre,
        tipo_eliminacion=tipo_eliminacion,
        rondas=rondas,
    )


class TestCrearTorneo(unittest.TestCase):
    def setUp(self):
        self.original_repository = tournament_service_module.TournamentRepository
        self.original_audit_repository = tournament_service_module.AuditLogRepository
        self.original_datetime = tournament_service_module.datetime

    def tearDown(self):
        tournament_service_module.TournamentRepository = self.original_repository
        tournament_service_module.AuditLogRepository = self.original_audit_repository
        tournament_service_module.datetime = self.original_datetime

    def test_crear_torneo_exitoso_persiste_estado_pendiente_y_auditoria(self):
        fake_repo = FakeTournamentRepository()
        fake_audit = FakeAuditLogRepository()
        tournament_service_module.TournamentRepository = lambda db: fake_repo
        tournament_service_module.AuditLogRepository = lambda db: fake_audit
        tournament_service_module.datetime = FixedDateTime

        service = TournamentService(db=object())
        result = service.create_tournament(build_payload(), creador_id=7)

        self.assertEqual(result.id, 10)
        self.assertEqual(result.nombre, "Torneo Unitario")
        self.assertEqual(result.tipo_eliminacion, "Eliminación Doble")
        self.assertEqual(result.rondas, 5)
        self.assertEqual(result.estado, "Pendiente")
        self.assertEqual(result.creador_id, 7)
        self.assertIsNotNone(fake_repo.saved_tournament)
        self.assertEqual(fake_repo.saved_tournament.estado, "Pendiente")
        self.assertEqual(fake_audit.recorded_action, "CREAR_TORNEO")
        self.assertEqual(fake_audit.recorded_date, datetime(2026, 6, 7, 12, 0, 0))
        self.assertEqual(fake_audit.recorded_user_id, 7)

    def test_crear_torneo_rechaza_eliminacion_sencilla_con_rondas_excesivas(self):
        fake_repo = FakeTournamentRepository()
        tournament_service_module.TournamentRepository = lambda db: fake_repo
        tournament_service_module.AuditLogRepository = lambda db: FakeAuditLogRepository()

        service = TournamentService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.create_tournament(
                build_payload(tipo_eliminacion="Eliminación Sencilla", rondas=8),
                creador_id=7,
            )

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("admite máximo", str(context.exception.detail))

    def test_crear_torneo_rechaza_nombre_duplicado(self):
        fake_repo = FakeTournamentRepository(existing_tournament=DummyTournament())
        tournament_service_module.TournamentRepository = lambda db: fake_repo
        tournament_service_module.AuditLogRepository = lambda db: FakeAuditLogRepository()

        service = TournamentService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.create_tournament(build_payload(nombre="Torneo Unitario"), creador_id=7)

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Ya existe un torneo activo", str(context.exception.detail))

    def test_esquema_rechaza_nombre_vacio(self):
        with self.assertRaises(ValidationError):
            TournamentCreate.model_validate(
                {"nombre": "", "tipo_eliminacion": "Doble Eliminación", "rondas": 5}
            )

    def test_esquema_rechaza_tipo_eliminacion_vacio(self):
        with self.assertRaises(ValidationError):
            TournamentCreate.model_validate(
                {"nombre": "Torneo Unitario", "tipo_eliminacion": "", "rondas": 5}
            )

    def test_esquema_rechaza_rondas_no_validas(self):
        with self.assertRaises(ValidationError):
            TournamentCreate.model_validate(
                {"nombre": "Torneo Unitario", "tipo_eliminacion": "Doble Eliminación", "rondas": 0}
            )


if __name__ == "__main__":
    unittest.main()
