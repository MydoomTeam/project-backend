import unittest
from dataclasses import dataclass

from fastapi import HTTPException, status

import app.services.registration_service as registration_service_module
from app.models.registration import RegistrationModel
from app.services.registration_service import RegistrationService


@dataclass
class DummyTournament:
    id: int = 9
    status: str = "Pendiente"
    creator_id: int = 99


@dataclass
class DummyRegistration:
    id: int = 1
    tournament_id: int = 9
    player_id: int = 5
    status: str = "Confirmado"


class FakeRegistrationRepository:
    def __init__(self, already_registered: bool = False):
        self.already_registered = already_registered
        self.saved_registration = None

    def active_registration_exists(self, tournament_id: int, player_id: int) -> bool:
        return self.already_registered

    def get_registration(self, tournament_id: int, player_id: int):
        return None

    def save(self, registration: RegistrationModel) -> RegistrationModel:
        self.saved_registration = registration
        return DummyRegistration(
            id=1,
            tournament_id=registration.tournament_id,
            player_id=registration.player_id,
            status=registration.status,
        )


class FakeTournamentRepository:
    def __init__(self, tournament: DummyTournament | None):
        self.tournament = tournament

    def get_by_id(self, tournament_id: int):
        return self.tournament


class TestRegistrationService(unittest.TestCase):
    def setUp(self):
        self.original_registration_repository = registration_service_module.RegistrationRepository
        self.original_tournament_repository = registration_service_module.TournamentRepository

    def tearDown(self):
        registration_service_module.RegistrationRepository = self.original_registration_repository
        registration_service_module.TournamentRepository = self.original_tournament_repository

    def test_successful_registration_forces_confirmed_status(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=False)
        fake_tournament_repo = FakeTournamentRepository(DummyTournament(status="Pendiente"))
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())
        result = service.register(9, player_id=5)

        self.assertEqual(result.id, 1)
        self.assertEqual(result.tournament_id, 9)
        self.assertEqual(result.player_id, 5)
        self.assertEqual(result.status, "Confirmado")
        self.assertEqual(fake_registration_repo.saved_registration.tournament_id, 9)
        self.assertEqual(fake_registration_repo.saved_registration.player_id, 5)
        self.assertEqual(fake_registration_repo.saved_registration.status, "Confirmado")

    def test_registration_rejects_nonexistent_tournament(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=False)
        fake_tournament_repo = FakeTournamentRepository(None)
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.register(9, player_id=5)

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            context.exception.detail,
            "El torneo no existe o no está disponible para inscripción",
        )

    def test_registration_rejects_non_pending_tournament(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=False)
        fake_tournament_repo = FakeTournamentRepository(DummyTournament(status="Activo"))
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.register(9, player_id=5)

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            context.exception.detail,
            "El torneo no existe o no está disponible para inscripción",
        )

    def test_registration_rejects_already_registered_player(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=True)
        fake_tournament_repo = FakeTournamentRepository(DummyTournament(status="Pendiente"))
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.register(9, player_id=5)

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(context.exception.detail, "El jugador ya está inscrito en este torneo")

    def test_registration_rejects_tournament_admin(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=False)
        fake_tournament_repo = FakeTournamentRepository(DummyTournament(status="Pendiente", creator_id=5))
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.register(9, player_id=5)

        self.assertEqual(context.exception.status_code, status.HTTP_403_FORBIDDEN)



if __name__ == "__main__":
    unittest.main()
