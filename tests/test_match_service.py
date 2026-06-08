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
        self.estado_actualizado = None
        self.auditoria_accion = None
        self.auditoria_usuario = None

    def obtener_por_id(self, torneo_id: int):
        return self.torneo

    def obtener_participantes_confirmados(self, torneo_id: int):
        return self.participantes

    def actualizar_estado_con_auditoria(self, torneo, nuevo_estado, accion, fecha, usuario_id):
        self.estado_actualizado = nuevo_estado
        self.auditoria_accion = accion
        self.auditoria_usuario = usuario_id
        torneo.estado = nuevo_estado
        return torneo


class FakeMatchRepository:
    def __init__(self):
        self.matches_insertados = []

    def insertar_en_lote(self, matches):
        for i, m in enumerate(matches):
            m.id = i + 1
        self.matches_insertados = matches
        return matches


def _service_sin_db():
    return object.__new__(MatchService)


class TestSiguientePotenciaDeDos(unittest.TestCase):
    def test_potencia_exacta_no_cambia(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(8), 8)

    def test_potencia_exacta_dos(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(2), 2)

    def test_potencia_exacta_uno(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(1), 1)

    def test_tres_sube_a_cuatro(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(3), 4)

    def test_cinco_sube_a_ocho(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(5), 8)

    def test_seis_sube_a_ocho(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(6), 8)

    def test_siete_sube_a_ocho(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(7), 8)

    def test_nueve_sube_a_dieciseis(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(9), 16)


class TestConstruirRonda1(unittest.TestCase):
    def test_cuatro_jugadores_genera_dos_matches_sin_byes(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = _service_sin_db()._construir_ronda1(1, participantes)

        self.assertEqual(len(matches), 2)
        self.assertTrue(all(m.jugador2_id is not None for m in matches))

    def test_cinco_jugadores_genera_tres_byes_y_un_match_real(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = _service_sin_db()._construir_ronda1(1, participantes)

        byes = [m for m in matches if m.jugador2_id is None]
        reales = [m for m in matches if m.jugador2_id is not None]
        self.assertEqual(len(byes), 3)
        self.assertEqual(len(reales), 1)

    def test_seis_jugadores_genera_dos_byes_y_dos_matches_reales(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200), (6, 1000)]
        matches = _service_sin_db()._construir_ronda1(1, participantes)

        byes = [m for m in matches if m.jugador2_id is None]
        reales = [m for m in matches if m.jugador2_id is not None]
        self.assertEqual(len(byes), 2)
        self.assertEqual(len(reales), 2)

    def test_byes_se_asignan_a_los_jugadores_de_mayor_elo(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = _service_sin_db()._construir_ronda1(1, participantes)

        ids_con_bye = {m.jugador1_id for m in matches if m.jugador2_id is None}
        self.assertIn(1, ids_con_bye)
        self.assertIn(2, ids_con_bye)
        self.assertIn(3, ids_con_bye)

    def test_jugadores_de_menor_elo_juegan_entre_si_en_ronda_1(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = _service_sin_db()._construir_ronda1(1, participantes)

        match_real = next(m for m in matches if m.jugador2_id is not None)
        self.assertIn(match_real.jugador1_id, {4, 5})
        self.assertIn(match_real.jugador2_id, {4, 5})

    def test_todos_los_matches_tienen_ronda_1(self):
        participantes = [(1, 1500), (2, 1400), (3, 1300), (4, 1200)]
        matches = _service_sin_db()._construir_ronda1(1, participantes)

        self.assertTrue(all(m.ronda == 1 for m in matches))

    def test_todos_los_matches_tienen_estado_programado(self):
        participantes = [(1, 1500), (2, 1400), (3, 1300), (4, 1200)]
        matches = _service_sin_db()._construir_ronda1(1, participantes)

        self.assertTrue(all(m.estado == "Programado" for m in matches))

    def test_dos_jugadores_genera_un_solo_match_sin_bye(self):
        participantes = [(1, 1500), (2, 1200)]
        matches = _service_sin_db()._construir_ronda1(1, participantes)

        self.assertEqual(len(matches), 1)
        self.assertIsNotNone(matches[0].jugador2_id)


class TestGenerarBracket(unittest.TestCase):
    def setUp(self):
        self.original_torneo_repo = match_service_module.TournamentRepository
        self.original_match_repo = match_service_module.MatchRepository

    def tearDown(self):
        match_service_module.TournamentRepository = self.original_torneo_repo
        match_service_module.MatchRepository = self.original_match_repo

    def _inyectar(self, torneo_repo, match_repo):
        match_service_module.TournamentRepository = lambda db: torneo_repo
        match_service_module.MatchRepository = lambda db: match_repo

    def test_lanza_404_si_torneo_no_existe(self):
        self._inyectar(FakeTournamentRepository(torneo=None), FakeMatchRepository())
        service = MatchService(db=object())

        with self.assertRaises(HTTPException) as ctx:
            service.generar_bracket(99, admin_id=10)

        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_lanza_403_si_usuario_no_es_el_creador_del_torneo(self):
        torneo = DummyTorneo(creador_id=10)
        self._inyectar(FakeTournamentRepository(torneo=torneo), FakeMatchRepository())
        service = MatchService(db=object())

        with self.assertRaises(HTTPException) as ctx:
            service.generar_bracket(1, admin_id=99)

        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

    def test_lanza_400_si_torneo_no_esta_en_estado_pendiente(self):
        torneo = DummyTorneo(estado="Listo para iniciar", creador_id=10)
        self._inyectar(FakeTournamentRepository(torneo=torneo), FakeMatchRepository())
        service = MatchService(db=object())

        with self.assertRaises(HTTPException) as ctx:
            service.generar_bracket(1, admin_id=10)

        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lanza_400_si_hay_menos_de_dos_participantes_confirmados(self):
        torneo = DummyTorneo(creador_id=10)
        repo = FakeTournamentRepository(torneo=torneo, participantes=[(1, 1500)])
        self._inyectar(repo, FakeMatchRepository())
        service = MatchService(db=object())

        with self.assertRaises(HTTPException) as ctx:
            service.generar_bracket(1, admin_id=10)

        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bracket_exitoso_devuelve_estado_listo_para_iniciar(self):
        torneo = DummyTorneo(creador_id=10)
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        self._inyectar(
            FakeTournamentRepository(torneo=torneo, participantes=participantes),
            FakeMatchRepository(),
        )
        service = MatchService(db=object())

        result = service.generar_bracket(1, admin_id=10)

        self.assertEqual(result.estado_torneo, "Listo para iniciar")

    def test_bracket_exitoso_registra_auditoria_con_accion_correcta(self):
        torneo = DummyTorneo(creador_id=10)
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        torneo_repo = FakeTournamentRepository(torneo=torneo, participantes=participantes)
        self._inyectar(torneo_repo, FakeMatchRepository())
        service = MatchService(db=object())

        service.generar_bracket(1, admin_id=10)

        self.assertEqual(torneo_repo.auditoria_accion, "GENERAR_BRACKET")
        self.assertEqual(torneo_repo.auditoria_usuario, 10)

    def test_bracket_con_cuatro_jugadores_genera_dos_matches(self):
        torneo = DummyTorneo(creador_id=10)
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        self._inyectar(
            FakeTournamentRepository(torneo=torneo, participantes=participantes),
            FakeMatchRepository(),
        )
        service = MatchService(db=object())

        result = service.generar_bracket(1, admin_id=10)

        self.assertEqual(len(result.matches), 2)

    def test_bracket_con_cinco_jugadores_genera_tres_byes(self):
        torneo = DummyTorneo(creador_id=10)
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        self._inyectar(
            FakeTournamentRepository(torneo=torneo, participantes=participantes),
            FakeMatchRepository(),
        )
        service = MatchService(db=object())

        result = service.generar_bracket(1, admin_id=10)

        byes = [m for m in result.matches if m.jugador2_id is None]
        self.assertEqual(len(byes), 3)

    def test_bracket_asigna_torneo_id_correcto_en_todos_los_matches(self):
        torneo = DummyTorneo(id=7, creador_id=10)
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        self._inyectar(
            FakeTournamentRepository(torneo=torneo, participantes=participantes),
            FakeMatchRepository(),
        )
        service = MatchService(db=object())

        result = service.generar_bracket(7, admin_id=10)

        self.assertTrue(all(m.torneo_id == 7 for m in result.matches))


if __name__ == "__main__":
    unittest.main()
