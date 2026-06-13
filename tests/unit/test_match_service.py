import unittest
from dataclasses import dataclass

from fastapi import HTTPException, status

import app.services.match_service as match_service_module
from app.services.match_service import MatchService


@dataclass
class DummyTournament:
    id: int = 1
    name: str = "Torneo Test"
    elimination_type: str = "Eliminación Sencilla"
    rounds: int = 3
    status: str = "Pendiente"
    creator_id: int = 10


@dataclass
class DummyMatch:
    id: int = 1
    tournament_id: int = 1
    round: int = 1
    position: int = 0
    bracket_type: str = "ganadores"
    player1_id: int = 1
    player2_id: int = 2
    winner_id: int | None = None
    status: str = "En curso"


@dataclass
class DummyPlayer:
    id: int = 1
    global_elo: int = 1000


class FakeDb:
    def add(self, _): pass
    def flush(self): pass
    def commit(self): pass
    def refresh(self, _): pass


class FakeTournamentRepository:
    def __init__(self, tournament=None, participants=None):
        self.tournament = tournament
        self.participants = participants or []

    def get_by_id(self, _):
        return self.tournament

    def get_confirmed_participants(self, _):
        return self.participants

    def update_status(self, tournament, new_status):
        tournament.status = new_status
        return tournament


class FakeAuditLogRepository:
    def __init__(self):
        self.actions: list[str] = []

    def record(self, action, user_id, created_at):
        self.actions.append(action)


class FakeMatchRepository:
    def __init__(self, match=None, next_match=None):
        self._match = match
        self._next_match = next_match
        self.inserted: list = []

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, _):
        pass

    def insert_batch(self, matches):
        for i, m in enumerate(matches):
            m.id = i + 1
        self.inserted = matches
        return matches

    def get_by_id(self, _):
        return self._match

    def get_by_tournament(self, _):
        return self.inserted

    def get_by_tournament_round(self, _, __):
        return []

    def get_by_tournament_round_position(self, **__):
        return self._next_match

    def get_by_tournament_round_position_bracket(self, **__):
        return self._next_match

    def get_round1_byes(self, _):
        return []

    def count_active_by_tournament(self, _):
        return 0

    def count_active_by_round(self, _, __):
        return 0

    def get_max_round(self, _):
        return 1

    def get_wins_by_player(self, _):
        return {}

    def get_played_pairs(self, _):
        return set()

    def get_player_history(self, _, __):
        return []


class FakePlayerRepository:
    def __init__(self, players: list[DummyPlayer] | None = None):
        self._store = {j.id: j for j in (players or [])}

    def get_by_id(self, jugador_id: int):
        return self._store.get(jugador_id)


class TestGenerateBracket(unittest.TestCase):
    def setUp(self):
        self.original_tournament_repo = match_service_module.TournamentRepository
        self.original_match_repo = match_service_module.MatchRepository
        self.original_player_repo = match_service_module.PlayerRepository
        self.original_audit_repo = match_service_module.AuditLogRepository
        self.fake_audit = FakeAuditLogRepository()

    def tearDown(self):
        match_service_module.TournamentRepository = self.original_tournament_repo
        match_service_module.MatchRepository = self.original_match_repo
        match_service_module.PlayerRepository = self.original_player_repo
        match_service_module.AuditLogRepository = self.original_audit_repo

    def _inject(self, tournament_repo, match_repo=None):
        match_service_module.TournamentRepository = lambda db: tournament_repo
        match_service_module.MatchRepository = lambda db: match_repo or FakeMatchRepository()
        match_service_module.PlayerRepository = lambda db: FakePlayerRepository()
        match_service_module.AuditLogRepository = lambda db: self.fake_audit

    def test_raises_404_if_tournament_not_found(self):
        self._inject(FakeTournamentRepository(tournament=None))
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).generate_bracket(99, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_raises_403_if_user_is_not_creator(self):
        self._inject(FakeTournamentRepository(tournament=DummyTournament(creator_id=10)))
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).generate_bracket(1, admin_id=99)
        self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

    def test_raises_400_if_insufficient_participants(self):
        repo = FakeTournamentRepository(tournament=DummyTournament(creator_id=10), participants=[(1, 1500)])
        self._inject(repo)
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).generate_bracket(1, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_bracket_generates_all_rounds_and_logs_audit(self):
        tournament_repo = FakeTournamentRepository(
            tournament=DummyTournament(creator_id=10),
            participants=[(1, 2000), (2, 1800), (3, 1600), (4, 1400)],
        )
        self._inject(tournament_repo)
        result = MatchService(db=FakeDb()).generate_bracket(1, admin_id=10)

        self.assertEqual(result.tournament_status, "Listo para iniciar")
        self.assertEqual({m.round for m in result.matches}, {1, 2})
        self.assertIn("GENERAR_BRACKET", self.fake_audit.actions)


class TestRecordResult(unittest.TestCase):
    def setUp(self):
        self.original_tournament_repo = match_service_module.TournamentRepository
        self.original_match_repo = match_service_module.MatchRepository
        self.original_player_repo = match_service_module.PlayerRepository

    def tearDown(self):
        match_service_module.TournamentRepository = self.original_tournament_repo
        match_service_module.MatchRepository = self.original_match_repo
        match_service_module.PlayerRepository = self.original_player_repo

    def _inject(self, tournament_repo, match_repo, player_repo):
        match_service_module.TournamentRepository = lambda db: tournament_repo
        match_service_module.MatchRepository = lambda db: match_repo
        match_service_module.PlayerRepository = lambda db: player_repo

    def test_raises_400_if_winner_is_not_participant(self):
        tournament_repo = FakeTournamentRepository(tournament=DummyTournament(status="En curso", creator_id=10))
        match_repo = FakeMatchRepository(match=DummyMatch(player1_id=1, player2_id=2))
        self._inject(tournament_repo, match_repo, FakePlayerRepository())
        with self.assertRaises(HTTPException) as ctx:
            MatchService(db=FakeDb()).record_result(1, 1, winner_id=99, admin_id=10)
        self.assertEqual(ctx.exception.status_code, status.HTTP_400_BAD_REQUEST)

    def test_updates_elo_of_both_players(self):
        tournament_repo = FakeTournamentRepository(tournament=DummyTournament(status="En curso", creator_id=10))
        match = DummyMatch(player1_id=1, player2_id=2, round=1, position=0)
        match_repo = FakeMatchRepository(match=match, next_match=DummyMatch(id=99, round=2, position=0))
        players = [DummyPlayer(id=1, global_elo=1000), DummyPlayer(id=2, global_elo=1000)]
        self._inject(tournament_repo, match_repo, FakePlayerRepository(players))

        result = MatchService(db=FakeDb()).record_result(1, 1, winner_id=1, admin_id=10)

        self.assertGreater(result.winner_new_elo, 1000)
        self.assertLess(result.loser_new_elo, 1000)

    def test_finalizes_tournament_when_no_next_match(self):
        tournament = DummyTournament(status="En curso", creator_id=10)
        tournament_repo = FakeTournamentRepository(tournament=tournament)
        match = DummyMatch(player1_id=1, player2_id=2, round=3, position=0)
        match_repo = FakeMatchRepository(match=match, next_match=None)
        players = [DummyPlayer(id=1, global_elo=1500), DummyPlayer(id=2, global_elo=1200)]
        self._inject(tournament_repo, match_repo, FakePlayerRepository(players))

        result = MatchService(db=FakeDb()).record_result(1, 1, winner_id=1, admin_id=10)

        self.assertTrue(result.tournament_finished)
        self.assertEqual(tournament.status, "Finalizado")


if __name__ == "__main__":
    unittest.main()
