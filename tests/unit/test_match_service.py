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


@dataclass
class DummyMatch:
    id: int = 1
    torneo_id: int = 1
    ronda: int = 1
    posicion: int = 0
    bracket_tipo: str = "ganadores"
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

    def obtener_por_id(self, _):
        return self.torneo

    def obtener_participantes_confirmados(self, _):
        return self.participantes

    def actualizar_estado(self, torneo, nuevo_estado):
        torneo.estado = nuevo_estado
        return torneo


class FakeAuditLogRepository:
    def __init__(self):
        self.actions: list[str] = []

    def record(self, accion, usuario_id, fecha):
        self.actions.append(accion)


class FakeMatchRepository:
    def __init__(self, match=None, siguiente=None):
        self._match = match
        self._siguiente = siguiente
        self.inserted: list = []

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, _):
        pass

    def insertar_en_lote(self, matches):
        for i, m in enumerate(matches):
            m.id = i + 1
        self.inserted = matches
        return matches

    def obtener_por_id(self, _):
        return self._match

    def obtener_por_torneo(self, _):
        return self.inserted

    def obtener_por_torneo_ronda(self, _, __):
        return []

    def obtener_por_torneo_ronda_posicion(self, **__):
        return self._siguiente

    def obtener_por_torneo_ronda_posicion_bracket(self, **__):
        return self._siguiente

    def obtener_byes_ronda1(self, _):
        return []

    def contar_activos_por_torneo(self, _):
        return 0

    def contar_activos_por_ronda(self, _, __):
        return 0

    def obtener_max_ronda(self, _):
        return 1

    def obtener_victorias_por_jugador(self, _):
        return {}

    def obtener_pares_jugados(self, _):
        return set()

    def obtener_historial_jugador(self, _, __):
        return []


class FakeJugadorRepository:
    def __init__(self, jugadores: list[DummyJugador] | None = None):
        self._store = {j.id: j for j in (jugadores or [])}

    def obtener_por_id(self, jugador_id: int):
        return self._store.get(jugador_id)


class TestGenerarBracket(unittest.TestCase):
    def setUp(self):
        self.original_torneo_repo = match_service_module.TournamentRepository
        self.original_match_repo = match_service_module.MatchRepository
        self.original_jugador_repo = match_service_module.JugadorRepository
        self.original_audit_repo = match_service_module.AuditLogRepository
        self.fake_audit = FakeAuditLogRepository()

    def tearDown(self):
        match_service_module.TournamentRepository = self.original_torneo_repo
        match_service_module.MatchRepository = self.original_match_repo
        match_service_module.JugadorRepository = self.original_jugador_repo
        match_service_module.AuditLogRepository = self.original_audit_repo

    def _inyectar(self, torneo_repo, match_repo=None):
        match_service_module.TournamentRepository = lambda db: torneo_repo
        match_service_module.MatchRepository = lambda db: match_repo or FakeMatchRepository()
        match_service_module.JugadorRepository = lambda db: FakeJugadorRepository()
        match_service_module.AuditLogRepository = lambda db: self.fake_audit

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
        self.assertEqual({m.ronda for m in result.matches}, {1, 2})
        self.assertIn("GENERAR_BRACKET", self.fake_audit.actions)


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

    def test_lanza_400_si_ganador_no_es_participante(self):
        torneo_repo = FakeTournamentRepository(torneo=DummyTorneo(estado="En curso", creador_id=10))
        match_repo = FakeMatchRepository(match=DummyMatch(jugador1_id=1, jugador2_id=2))
        self._inyectar(torneo_repo, match_repo, FakeJugadorRepository())
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).registrar_resultado(1, 1, ganador_id=99, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_actualiza_elo_de_ambos_jugadores(self):
        torneo_repo = FakeTournamentRepository(torneo=DummyTorneo(estado="En curso", creador_id=10))
        match = DummyMatch(jugador1_id=1, jugador2_id=2, ronda=1, posicion=0)
        match_repo = FakeMatchRepository(match=match, siguiente=DummyMatch(id=99, ronda=2, posicion=0))
        jugadores = [DummyJugador(id=1, elo_global=1000), DummyJugador(id=2, elo_global=1000)]
        self._inyectar(torneo_repo, match_repo, FakeJugadorRepository(jugadores))

        resultado = MatchService(db=FakeDb()).registrar_resultado(1, 1, ganador_id=1, admin_id=10)

        self.assertGreater(resultado.ganador_nuevo_elo, 1000)
        self.assertLess(resultado.perdedor_nuevo_elo, 1000)

    def test_finaliza_torneo_cuando_no_hay_siguiente_match(self):
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
