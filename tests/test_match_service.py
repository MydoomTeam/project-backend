import unittest
from dataclasses import dataclass, field

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


@dataclass
class DummyMatch:
    id: int = 1
    torneo_id: int = 1
    ronda: int = 1
    posicion: int = 0
    jugador1_id: int = 1
    jugador2_id: int = 2
    ganador_id: int | None = None
    estado: str = "En curso"


@dataclass
class DummyJugador:
    id: int = 1
    elo_global: int = 1000


class FakeDb:
    def add(self, _): pass
    def flush(self): pass
    def commit(self): pass
    def refresh(self, _): pass


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
    def __init__(self, match=None, siguiente=None, byes=None, ronda1=None):
        self._match = match
        self._siguiente = siguiente
        self._byes = byes or []
        self._ronda1 = ronda1 or []
        self.inserted: list = []

    def insertar_en_lote(self, matches):
        for i, m in enumerate(matches):
            m.id = i + 1
        self.inserted = matches
        return matches

    def obtener_por_id(self, match_id: int):
        return self._match

    def obtener_por_torneo(self, torneo_id: int):
        return self.inserted

    def obtener_por_torneo_ronda(self, torneo_id: int, ronda: int):
        return self._ronda1

    def obtener_por_torneo_ronda_posicion(self, torneo_id, ronda, posicion):
        return self._siguiente

    def obtener_byes_ronda1(self, torneo_id: int):
        return self._byes


class FakeJugadorRepository:
    def __init__(self, jugadores: list[DummyJugador] | None = None):
        self._store = {j.id: j for j in (jugadores or [])}

    def obtener_por_id(self, jugador_id: int):
        return self._store.get(jugador_id)


class TestSiguientePotenciaDeDos(unittest.TestCase):
    def test_valor_ya_es_potencia_de_dos(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(8), 8)

    def test_valor_entre_potencias_sube_a_la_siguiente(self):
        self.assertEqual(MatchService._siguiente_potencia_de_dos(5), 8)


class TestCalcularNuevoElo(unittest.TestCase):
    def test_igual_habilidad_distribuye_k_entre_dos(self):
        nuevo_g, nuevo_p = MatchService._calcular_nuevo_elo(1000, 1000)
        self.assertEqual(nuevo_g, 1016)
        self.assertEqual(nuevo_p, 984)

    def test_ganador_con_menor_elo_recibe_mas_puntos(self):
        nuevo_g, _ = MatchService._calcular_nuevo_elo(1000, 1400)
        self.assertGreater(nuevo_g - 1000, 16)

    def test_suma_neta_de_elo_es_cero(self):
        nuevo_g, nuevo_p = MatchService._calcular_nuevo_elo(1200, 1000)
        delta = (nuevo_g - 1200) + (nuevo_p - 1000)
        self.assertEqual(delta, 0)


class TestConstruirBracketCompleto(unittest.TestCase):
    def _service(self):
        return object.__new__(MatchService)

    def test_cuatro_jugadores_genera_tres_matches_en_dos_rondas(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_bracket_completo(1, participantes)

        rondas = {m.ronda for m in matches}
        self.assertEqual(rondas, {1, 2})
        self.assertEqual(len(matches), 3)

    def test_cinco_jugadores_genera_siete_matches_en_tres_rondas(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._construir_bracket_completo(1, participantes)

        self.assertEqual(len(matches), 7)
        self.assertEqual(max(m.ronda for m in matches), 3)

    def test_rondas_futuras_inician_sin_jugadores_asignados(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400)]
        matches = self._service()._construir_bracket_completo(1, participantes)

        ronda2 = [m for m in matches if m.ronda == 2]
        self.assertTrue(all(m.jugador1_id is None and m.jugador2_id is None for m in ronda2))

    def test_byes_asignados_a_seeds_de_mayor_elo(self):
        participantes = [(1, 2000), (2, 1800), (3, 1600), (4, 1400), (5, 1200)]
        matches = self._service()._construir_bracket_completo(1, participantes)

        byes = [m for m in matches if m.ronda == 1 and m.jugador2_id is None]
        ids_con_bye = {m.jugador1_id for m in byes}
        self.assertEqual(len(byes), 3)
        self.assertIn(1, ids_con_bye)
        self.assertIn(2, ids_con_bye)
        self.assertIn(3, ids_con_bye)


class TestGenerarBracket(unittest.TestCase):
    def setUp(self):
        self.original_torneo_repo = match_service_module.TournamentRepository
        self.original_match_repo = match_service_module.MatchRepository
        self.original_jugador_repo = match_service_module.JugadorRepository

    def tearDown(self):
        match_service_module.TournamentRepository = self.original_torneo_repo
        match_service_module.MatchRepository = self.original_match_repo
        match_service_module.JugadorRepository = self.original_jugador_repo

    def _inyectar(self, torneo_repo, match_repo=None):
        match_service_module.TournamentRepository = lambda db: torneo_repo
        match_service_module.MatchRepository = lambda db: match_repo or FakeMatchRepository()
        match_service_module.JugadorRepository = lambda db: FakeJugadorRepository()

    def test_lanza_404_si_torneo_no_existe(self):
        self._inyectar(FakeTournamentRepository(torneo=None))
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).generar_bracket(99, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_lanza_403_si_usuario_no_es_el_creador(self):
        self._inyectar(FakeTournamentRepository(torneo=DummyTorneo(creador_id=10)))
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).generar_bracket(1, admin_id=99)
        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

    def test_lanza_400_si_participantes_insuficientes(self):
        repo = FakeTournamentRepository(torneo=DummyTorneo(creador_id=10), participantes=[(1, 1500)])
        self._inyectar(repo)
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).generar_bracket(1, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bracket_exitoso_genera_todas_las_rondas_y_registra_auditoria(self):
        torneo_repo = FakeTournamentRepository(
            torneo=DummyTorneo(creador_id=10),
            participantes=[(1, 2000), (2, 1800), (3, 1600), (4, 1400)],
        )
        self._inyectar(torneo_repo)
        result = MatchService(db=FakeDb()).generar_bracket(1, admin_id=10)

        self.assertEqual(result.estado_torneo, "Listo para iniciar")
        rondas = {m.ronda for m in result.matches}
        self.assertEqual(rondas, {1, 2})
        self.assertEqual(torneo_repo.auditoria_accion, "GENERAR_BRACKET")


class TestRegistrarResultado(unittest.TestCase):
    def setUp(self):
        self.original_torneo_repo = match_service_module.TournamentRepository
        self.original_match_repo = match_service_module.MatchRepository
        self.original_jugador_repo = match_service_module.JugadorRepository

    def tearDown(self):
        match_service_module.TournamentRepository = self.original_torneo_repo
        match_service_module.MatchRepository = self.original_match_repo
        match_service_module.JugadorRepository = self.original_jugador_repo

    def _inyectar(self, torneo_repo, match_repo, jugador_repo):
        match_service_module.TournamentRepository = lambda db: torneo_repo
        match_service_module.MatchRepository = lambda db: match_repo
        match_service_module.JugadorRepository = lambda db: jugador_repo

    def test_lanza_403_si_no_es_administrador(self):
        torneo_repo = FakeTournamentRepository(torneo=DummyTorneo(estado="En curso", creador_id=10))
        match_repo = FakeMatchRepository(match=DummyMatch())
        self._inyectar(torneo_repo, match_repo, FakeJugadorRepository())
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).registrar_resultado(1, 1, ganador_id=1, admin_id=99)
        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

    def test_lanza_400_si_ganador_no_es_participante(self):
        torneo_repo = FakeTournamentRepository(torneo=DummyTorneo(estado="En curso", creador_id=10))
        match_repo = FakeMatchRepository(match=DummyMatch(jugador1_id=1, jugador2_id=2))
        self._inyectar(torneo_repo, match_repo, FakeJugadorRepository())
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).registrar_resultado(1, 1, ganador_id=99, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_actualiza_elo_de_ganador_y_perdedor(self):
        torneo_repo = FakeTournamentRepository(torneo=DummyTorneo(estado="En curso", creador_id=10))
        match = DummyMatch(jugador1_id=1, jugador2_id=2, ronda=1, posicion=0)
        match_repo = FakeMatchRepository(match=match, siguiente=DummyMatch(id=99, ronda=2, posicion=0))
        jugador_g = DummyJugador(id=1, elo_global=1000)
        jugador_p = DummyJugador(id=2, elo_global=1000)
        self._inyectar(torneo_repo, match_repo, FakeJugadorRepository([jugador_g, jugador_p]))

        resultado = MatchService(db=FakeDb()).registrar_resultado(1, 1, ganador_id=1, admin_id=10)

        self.assertEqual(resultado.ganador_nuevo_elo, 1016)
        self.assertEqual(resultado.perdedor_nuevo_elo, 984)
        self.assertEqual(jugador_g.elo_global, 1016)
        self.assertEqual(jugador_p.elo_global, 984)

    def test_avanza_ganador_a_slot_correcto_en_siguiente_ronda(self):
        torneo_repo = FakeTournamentRepository(torneo=DummyTorneo(estado="En curso", creador_id=10))
        match = DummyMatch(jugador1_id=1, jugador2_id=2, ronda=1, posicion=1)
        siguiente = DummyMatch(id=99, ronda=2, posicion=0, jugador1_id=3, jugador2_id=None, estado="Pendiente")
        match_repo = FakeMatchRepository(match=match, siguiente=siguiente)
        jugadores = [DummyJugador(id=1, elo_global=1000), DummyJugador(id=2, elo_global=1000)]
        self._inyectar(torneo_repo, match_repo, FakeJugadorRepository(jugadores))

        MatchService(db=FakeDb()).registrar_resultado(1, 1, ganador_id=1, admin_id=10)

        self.assertEqual(siguiente.jugador2_id, 1)

    def test_marca_torneo_finalizado_cuando_es_la_final(self):
        torneo = DummyTorneo(estado="En curso", creador_id=10)
        torneo_repo = FakeTournamentRepository(torneo=torneo)
        match = DummyMatch(jugador1_id=1, jugador2_id=2, ronda=3, posicion=0)
        match_repo = FakeMatchRepository(match=match, siguiente=None)
        jugadores = [DummyJugador(id=1, elo_global=1500), DummyJugador(id=2, elo_global=1200)]
        self._inyectar(torneo_repo, match_repo, FakeJugadorRepository(jugadores))

        resultado = MatchService(db=FakeDb()).registrar_resultado(1, 1, ganador_id=1, admin_id=10)

        self.assertTrue(resultado.torneo_finalizado)
        self.assertEqual(torneo.estado, "Finalizado")


if __name__ == "__main__":
    unittest.main()
