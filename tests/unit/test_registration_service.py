import unittest
from dataclasses import dataclass

from fastapi import HTTPException, status
from pydantic import ValidationError

import app.services.registration_service as registration_service_module
from app.models.registration import RegistrationModel
from app.schemas.registration import RegistrationCreate
from app.services.registration_service import RegistrationService


@dataclass
class DummyTournament:
    id: int = 9
    estado: str = "Pendiente"
    creador_id: int = 99


@dataclass
class DummyRegistration:
    id: int = 1
    torneo_id: int = 9
    jugador_id: int = 5
    estado: str = "Confirmado"


class FakeRegistrationRepository:
    def __init__(self, already_registered: bool = False):
        self.already_registered = already_registered
        self.saved_registration = None

    def active_registration_exists(self, torneo_id: int, jugador_id: int) -> bool:
        return self.already_registered

    def get_registration(self, torneo_id: int, jugador_id: int):
        return None

    def save(self, inscripcion: RegistrationModel) -> RegistrationModel:
        self.saved_registration = inscripcion
        return DummyRegistration(
            id=1,
            torneo_id=inscripcion.torneo_id,
            jugador_id=inscripcion.jugador_id,
            estado=inscripcion.estado,
        )


class FakeTournamentRepository:
    def __init__(self, tournament: DummyTournament | None):
        self.tournament = tournament

    def get_by_id(self, torneo_id: int):
        return self.tournament


def build_payload(torneo_id: int = 9) -> RegistrationCreate:
    return RegistrationCreate(torneo_id=torneo_id)


class TestRegistrationService(unittest.TestCase):
    def setUp(self):
        self.original_registration_repository = registration_service_module.RegistrationRepository
        self.original_tournament_repository = registration_service_module.TournamentRepository

    def tearDown(self):
        registration_service_module.RegistrationRepository = self.original_registration_repository
        registration_service_module.TournamentRepository = self.original_tournament_repository

    def test_registro_exitoso_forza_estado_confirmado(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=False)
        fake_tournament_repo = FakeTournamentRepository(DummyTournament(estado="Pendiente"))
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())
        result = service.register(build_payload(), jugador_id=5)

        self.assertEqual(result.id, 1)
        self.assertEqual(result.torneo_id, 9)
        self.assertEqual(result.jugador_id, 5)
        self.assertEqual(result.estado, "Confirmado")
        self.assertEqual(fake_registration_repo.saved_registration.torneo_id, 9)
        self.assertEqual(fake_registration_repo.saved_registration.jugador_id, 5)
        self.assertEqual(fake_registration_repo.saved_registration.estado, "Confirmado")

    def test_registro_rechaza_torneo_inexistente(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=False)
        fake_tournament_repo = FakeTournamentRepository(None)
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.register(build_payload(), jugador_id=5)

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            context.exception.detail,
            "El torneo no existe o no está disponible para inscripción",
        )

    def test_registro_rechaza_torneo_no_pendiente(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=False)
        fake_tournament_repo = FakeTournamentRepository(DummyTournament(estado="Activo"))
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.register(build_payload(), jugador_id=5)

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            context.exception.detail,
            "El torneo no existe o no está disponible para inscripción",
        )

    def test_registro_rechaza_jugador_ya_inscrito(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=True)
        fake_tournament_repo = FakeTournamentRepository(DummyTournament(estado="Pendiente"))
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.register(build_payload(), jugador_id=5)

        self.assertEqual(context.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(context.exception.detail, "El jugador ya está inscrito en este torneo")

    def test_registro_rechaza_al_administrador_del_torneo(self):
        fake_registration_repo = FakeRegistrationRepository(already_registered=False)
        fake_tournament_repo = FakeTournamentRepository(DummyTournament(estado="Pendiente", creador_id=5))
        registration_service_module.RegistrationRepository = lambda db: fake_registration_repo
        registration_service_module.TournamentRepository = lambda db: fake_tournament_repo

        service = RegistrationService(db=object())

        with self.assertRaises(HTTPException) as context:
            service.register(build_payload(), jugador_id=5)

        self.assertEqual(context.exception.status_code, status.HTTP_403_FORBIDDEN)

    def test_esquema_rechaza_torneo_id_no_valido(self):
        with self.assertRaises(ValidationError):
            RegistrationCreate.model_validate({"torneo_id": 0})

        with self.assertRaises(ValidationError):
            RegistrationCreate.model_validate({})


if __name__ == "__main__":
    unittest.main()
