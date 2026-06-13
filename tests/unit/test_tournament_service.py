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
    name: str = "Torneo Unitario"
    elimination_type: str = "Eliminación Doble"
    rounds: int = 5
    status: str = "Pendiente"
    creator_id: int = 1


class FakeTournamentRepository:
    def __init__(self, existing_tournament: TournamentModel | None = None):
        self.existing_tournament = existing_tournament
        self.saved_tournament = None

    def get_active_by_name(self, name: str):
        return self.existing_tournament

    def save(self, tournament):
        self.saved_tournament = tournament
        return DummyTournament(
            id=10,
            name=tournament.name,
            elimination_type=tournament.elimination_type,
            rounds=tournament.rounds,
            status=tournament.status,
            creator_id=tournament.creator_id,
        )


class FakeAuditLogRepository:
    def __init__(self):
        self.recorded_action = None
        self.recorded_date = None
        self.recorded_user_id = None

    def record(self, action, user_id, created_at):
        self.recorded_action = action
        self.recorded_user_id = user_id
        self.recorded_date = created_at


class FixedDateTime:
    @classmethod
    def now(cls):
        return datetime(2026, 6, 7, 12, 0, 0)


def build_payload(
    name: str = "Torneo Unitario",
    elimination_type: str = "Eliminación Doble",
    rounds: int = 5,
) -> TournamentCreate:
    return TournamentCreate(
        name=name,
        elimination_type=elimination_type,
        rounds=rounds,
    )


class TestCreateTournament(unittest.TestCase):
    def setUp(self):
        self.original_repository = tournament_service_module.TournamentRepository
        self.original_audit_repository = tournament_service_module.AuditLogRepository
        self.original_datetime = tournament_service_module.datetime

    def tearDown(self):
        tournament_service_module.TournamentRepository = self.original_repository
        tournament_service_module.AuditLogRepository = self.original_audit_repository
        tournament_service_module.datetime = self.original_datetime

    def test_successful_tournament_creation_persists_pending_status_and_audit(self):
        fake_repo = FakeTournamentRepository()
        fake_audit = FakeAuditLogRepository()
        tournament_service_module.TournamentRepository = lambda db: fake_repo
        tournament_service_module.AuditLogRepository = lambda db: fake_audit
        tournament_service_module.datetime = FixedDateTime

        service = TournamentService(db=object())
        result = service.create_tournament(build_payload(), creator_id=7)

        self.assertEqual(result.id, 10)
        self.assertEqual(result.name, "Torneo Unitario")
        self.assertEqual(result.elimination_type, "Eliminación Doble")
        self.assertEqual(result.rounds, 5)
        self.assertEqual(result.status, "Pendiente")
        self.assertEqual(result.creator_id, 7)
        self.assertIsNotNone(fake_repo.saved_tournament)
        self.assertEqual(fake_repo.saved_tournament.status, "Pendiente")
        self.assertEqual(fake_audit.recorded_action, "CREAR_TORNEO")
        self.assertEqual(fake_audit.recorded_date, datetime(2026, 6, 7, 12, 0, 0))
        self.assertEqual(fake_audit.recorded_user_id, 7)

    def test_tournament_creation_rejects_single_elimination_with_excessive_rounds(self):
        fake_repo = FakeTournamentRepository()
        tournament_service_module.TournamentRepository = lambda db: fake_repo
        tournament_service_module.AuditLogRepository = lambda db: FakeAuditLogRepository()

        service = TournamentService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.create_tournament(
                build_payload(elimination_type="Eliminación Sencilla", rounds=8),
                creator_id=7,
            )

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("admite máximo", str(context.exception.detail))

    def test_tournament_creation_rejects_duplicate_name(self):
        fake_repo = FakeTournamentRepository(existing_tournament=DummyTournament())
        tournament_service_module.TournamentRepository = lambda db: fake_repo
        tournament_service_module.AuditLogRepository = lambda db: FakeAuditLogRepository()

        service = TournamentService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.create_tournament(build_payload(name="Torneo Unitario"), creator_id=7)

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Ya existe un torneo activo", str(context.exception.detail))

    def test_schema_rejects_empty_name(self):
        with self.assertRaises(ValidationError):
            TournamentCreate.model_validate(
                {"name": "", "elimination_type": "Doble Eliminación", "rounds": 5}
            )

    def test_schema_rejects_empty_elimination_type(self):
        with self.assertRaises(ValidationError):
            TournamentCreate.model_validate(
                {"name": "Torneo Unitario", "elimination_type": "", "rounds": 5}
            )

    def test_schema_rejects_invalid_rounds(self):
        with self.assertRaises(ValidationError):
            TournamentCreate.model_validate(
                {"name": "Torneo Unitario", "elimination_type": "Doble Eliminación", "rounds": 0}
            )


if __name__ == "__main__":
    unittest.main()
