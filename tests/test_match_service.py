import unittest
from dataclasses import dataclass

from fastapi import HTTPException, status

import app.services.match_service as match_service_module
from app.services.match_service import MatchService


@dataclass
class DummyTorneo:
    id: int = 1
    nombre: str = "Torneo Test"
    tipo_eliminacion: str = "Eliminación Sencilla"
    rondas: int = 3
    estado: str = "Pendiente"
    creador_id: int = 10


class FakeTournamentRepository:
    def __init__(self, torneo=None, participantes=None):
        self.torneo = torneo
        self.participantes = participantes or []
        self.auditoria_accion = None
        self.auditoria_usuario = None

    def obtener_por_id(self, torneo_id: int):
        return self.torneo

    def obtener_participantes_confirmados(self, torneo_id: int):
        return self.participantes

    def actualizar_estado_con_auditoria(self, torneo, nuevo_estado, accion, fecha, usuario_id):
        self.auditoria_accion = accion
        self.auditoria_usuario = usuario_id
        torneo.estado = nuevo_estado
        return torneo


class FakeMatchRepository:
    def insertar_en_lote(self, matches):
        for i, m in enumerate(matches):
            m.id = i + 1
        return matches


class TestSiguientePotenciaDeDos(unittest.TestCase):
    def test_valor_ya_es_potencia_de_dos(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(8), 8)

    def test_valor_entre_potencias_sube_a_la_siguiente(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(5), 8)

    def test_valor_minimo_uno(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(1), 1)


class TestConstruirRonda1(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_cuatro_jugadores_genera_dos_matches_sin_byes(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_ronda1(1, participantes)

        self.assertEqual(len(matches), 2)
        self.assertTrue(all(m.jugador2_id is not None for m in matches))

    def test_cinco_jugadores_asigna_byes_a_los_de_mayor_elo(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._construir_ronda1(1, participantes)

        byes = [m for m in matches if m.jugador2_id is None]
        ids_con_bye = {m.jugador1_id for m in byes}
        self.assertEqual(len(byes), 3)
        self.assertIn(1, ids_con_bye)
        self.assertIn(2, ids_con_bye)
        self.assertIn(3, ids_con_bye)

    def test_todos_los_matches_tienen_estado_programado_y_ronda_1(self):
        participantes = [(1, 1500), (2, 1400), (3, 1300), (4, 1200)]
        matches = self._service()._construir_ronda1(1, participantes)

        self.assertTrue(all(m.estado == "Programado" and m.ronda == 1 for m in matches))


class TestGenerarBracket(unittest.TestCase):
    def setUp(self):
        self.original_torneo_repo = match_service_module.TournamentRepository
        self.original_match_repo = match_service_module.MatchRepository

    def tearDown(self):
        match_service_module.TournamentRepository = self.original_torneo_repo
        match_service_module.MatchRepository = self.original_match_repo

    def _inyectar(self, torneo_repo, match_repo=None):
        match_service_module.TournamentRepository = lambda db: torneo_repo
        match_service_module.MatchRepository = lambda db: match_repo or FakeMatchRepository()

    def test_lanza_404_si_torneo_no_existe(self):
        self._inyectar(FakeTournamentRepository(torneo=None))
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=object()).generar_bracket(99, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_lanza_403_si_usuario_no_es_el_creador(self):
        self._inyectar(FakeTournamentRepository(torneo=DummyTorneo(creador_id=10)))
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=object()).generar_bracket(1, admin_id=99)
        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

    def test_lanza_400_si_torneo_no_esta_pendiente(self):
        self._inyectar(FakeTournamentRepository(torneo=DummyTorneo(estado="Listo para iniciar", creador_id=10)))
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=object()).generar_bracket(1, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lanza_400_si_participantes_insuficientes(self):
        repo = FakeTournamentRepository(torneo=DummyTorneo(creador_id=10), participantes=[(1, 1500)])
        self._inyectar(repo)
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=object()).generar_bracket(1, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bracket_exitoso_actualiza_estado_y_registra_auditoria(self):
        torneo_repo = FakeTournamentRepository(
            torneo=DummyTorneo(creador_id=10),
            participantes=[(1, 2000), (2, 1800), (3, 1600), (4, 1400)],
        )
        self._inyectar(torneo_repo)
        result = MatchService(db=object()).generar_bracket(1, admin_id=10)

        self.assertEqual(result.estado_torneo, "Listo para iniciar")
        self.assertEqual(torneo_repo.auditoria_accion, "GENERAR_BRACKET")
        self.assertEqual(torneo_repo.auditoria_usuario, 10)


if __name__ == "__main__":
    unittest.main()
