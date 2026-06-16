from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.match import MatchModel
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.elo_history_repository import EloHistoryRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.player_repository import PlayerRepository
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.match import MatchResponse, ResultResponse
from app.schemas.tournament import BracketResponse, RankingEntry, RankingResponse

_ELO_SCALE = 400
_ELO_BASE = 10.0
_POINTS_WIN = 1.0
_POINTS_LOSS = 0.0

_ELO_K_NEW    = 40
_ELO_K_STANDARD = 32
_ELO_K_ELITE    = 16
_ELO_THRESHOLD_NEW  = 1000
_ELO_THRESHOLD_ELITE  = 2000

_MIN_PARTICIPANTS: dict[str, int] = {
    "Eliminación Sencilla": 2,
    "Eliminación Doble":    4,
    "Round Robin":          3,
    "Swiss":                4,
}

_BRACKET_WINNERS = "ganadores"
_BRACKET_LOSERS = "perdedores"
_BRACKET_GRAND_FINAL = "gran_final"

_FORMAT_SINGLE = "Eliminación Sencilla"
_FORMAT_DOUBLE    = "Eliminación Doble"
_FORMATS_WITH_BRACKET    = {_FORMAT_SINGLE, _FORMAT_DOUBLE}
_FORMATS_ROUND_ROBIN = {"Round Robin"}
_FORMATS_SWISS          = {"Swiss"}

_STATUS_PENDING = "Pendiente"
_STATUS_SCHEDULED = "Programado"
_STATUS_IN_PROGRESS = "En curso"
_STATUS_FINISHED = "Finalizado"
_STATUS_READY_TO_START = "Listo para iniciar"

_SLOT_PLAYER1 = 0
_SLOT_PLAYER2 = 1


class MatchService:
    def __init__(self, db: Session):
        self.tournament_repo  = TournamentRepository(db)
        self.match_repo   = MatchRepository(db)
        self.player_repo = PlayerRepository(db)
        self.audit_repo   = AuditLogRepository(db)
        self.elo_history_repo = EloHistoryRepository(db)

    def get_ranking(self, tournament_id: int) -> RankingResponse:
        tournament = self.tournament_repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")

        participants = self.tournament_repo.get_confirmed_participants(tournament_id)
        wins = self.match_repo.get_wins_by_player(tournament_id)

        entries = sorted(
            [{"player_id": jid, "wins": wins.get(jid, 0), "global_elo": elo} for jid, elo in participants],
            key=lambda e: (-e["wins"], -e["global_elo"]),
        )

        ranking = [
            RankingEntry(position=i + 1, player_id=e["player_id"], wins=e["wins"], global_elo=e["global_elo"])
            for i, e in enumerate(entries)
        ]
        return RankingResponse(tournament_id=tournament_id, elimination_type=tournament.elimination_type, status=tournament.status, ranking=ranking)

    def get_player_history(self, tournament_id: int, player_id: int) -> list[MatchResponse]:
        tournament = self.tournament_repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        matches = self.match_repo.get_player_history(tournament_id, player_id)
        return [MatchResponse.model_validate(m) for m in matches]

    def get_bracket(self, tournament_id: int) -> BracketResponse:
        tournament = self.tournament_repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        matches = self.match_repo.get_by_tournament(tournament_id)
        return BracketResponse(
            tournament_id=tournament_id,
            tournament_status=tournament.status,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def generate_bracket(self, tournament_id: int, admin_id: int) -> BracketResponse:
        tournament = self.tournament_repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if tournament.creator_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador del torneo puede generar el cuadro de enfrentamiento",
            )
        if tournament.status != _STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El periodo de inscripciones no está cerrado o el torneo ya fue procesado",
            )

        participants = self.tournament_repo.get_confirmed_participants(tournament_id)
        min_req = _MIN_PARTICIPANTS.get(tournament.elimination_type, 2)
        if len(participants) < min_req:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Se requieren al menos {min_req} participantes confirmados para {tournament.elimination_type}",
            )

        match_models = self._build_match_models(tournament, tournament_id, participants)

        match_models = self.match_repo.insert_batch(match_models)
        self._assign_next_match_ids(match_models, tournament.elimination_type)
        self.match_repo.flush()
        match_responses = [MatchResponse.model_validate(m) for m in match_models]

        self.audit_repo.record(
            action="GENERAR_BRACKET",
            user_id=admin_id,
            created_at=datetime.now(),
            change_description=f"tournament_id={tournament_id}",
        )
        tournament = self.tournament_repo.update_status(tournament, _STATUS_READY_TO_START)
        return BracketResponse(tournament_id=tournament_id, tournament_status=tournament.status, matches=match_responses)

    @staticmethod
    def _assign_next_match_ids(matches: list[MatchModel], elimination_type: str) -> None:
        if elimination_type not in {_FORMAT_SINGLE, _FORMAT_DOUBLE}:
            return

        winners_matches = [match for match in matches if match.bracket_type == _BRACKET_WINNERS]
        winners_index = {
            (match.round, match.position): match
            for match in winners_matches
        }

        grand_final = next(
            (match for match in matches if match.bracket_type == _BRACKET_GRAND_FINAL),
            None,
        )

        for match in winners_matches:
            next_match = winners_index.get((match.round + 1, match.position // 2))
            if next_match is not None:
                match.next_match_id = next_match.id
            elif elimination_type == _FORMAT_DOUBLE and grand_final is not None:
                match.next_match_id = grand_final.id
            else:
                match.next_match_id = None

        if elimination_type != _FORMAT_DOUBLE:
            return

        losers_matches = [match for match in matches if match.bracket_type == _BRACKET_LOSERS]
        losers_index = {
            (match.round, match.position): match
            for match in losers_matches
        }

        for match in losers_matches:
            if match.round % 2 == 1:
                next_key = (match.round + 1, match.position)
            else:
                next_key = (match.round + 1, match.position // 2)

            next_match = losers_index.get(next_key)
            if next_match is not None:
                match.next_match_id = next_match.id
            elif grand_final is not None:
                match.next_match_id = grand_final.id
            else:
                match.next_match_id = None

        if grand_final is not None:
            grand_final.next_match_id = None

    def _build_match_models(
        self, tournament, tournament_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        if tournament.elimination_type == _FORMAT_SINGLE:
            return self._build_full_bracket(tournament_id, participants)
        if tournament.elimination_type == _FORMAT_DOUBLE:
            return self._build_double_elimination(tournament_id, participants)
        if tournament.elimination_type in _FORMATS_ROUND_ROBIN:
            return self._build_round_robin(tournament_id, participants)
        if tournament.elimination_type in _FORMATS_SWISS:
            return self._build_swiss_round1(tournament_id, participants)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El formato '{tournament.elimination_type}' no tiene generación de bracket implementada",
        )

    def start_tournament(self, tournament_id: int, admin_id: int) -> BracketResponse:
        tournament = self.tournament_repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if tournament.creator_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede iniciar el torneo",
            )
        if tournament.status != _STATUS_READY_TO_START:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en estado 'Listo para iniciar'",
            )

        if tournament.elimination_type in _FORMATS_WITH_BRACKET:
            self._activate_round1_with_bracket(tournament_id)
        else:
            for m in self.match_repo.get_by_tournament(tournament_id):
                m.status = _STATUS_IN_PROGRESS

        tournament.status = _STATUS_IN_PROGRESS
        self.audit_repo.record(
            action="INICIAR_TORNEO",
            user_id=admin_id,
            created_at=datetime.now(),
            change_description=f"tournament_id={tournament_id}",
        )
        self.match_repo.flush()
        self.match_repo.commit()
        self.match_repo.refresh(tournament)

        matches = self.match_repo.get_by_tournament(tournament_id)
        return BracketResponse(
            tournament_id=tournament_id,
            tournament_status=tournament.status,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def _activate_round1_with_bracket(self, tournament_id: int) -> None:
        for bye in self.match_repo.get_round1_byes(tournament_id):
            bye.winner_id = bye.player1_id
            bye.status = _STATUS_FINISHED
            self._advance_winner_single(tournament_id, bye)
        for m in self.match_repo.get_by_tournament_round(tournament_id, round=1):
            if m.player2_id is not None and m.status != _STATUS_FINISHED:
                m.status = _STATUS_IN_PROGRESS

    def record_result(
        self,
        tournament_id: int,
        match_id: int,
        winner_id: int,
        admin_id: int,
        score_player1: int | None = None,
        score_player2: int | None = None,
    ) -> ResultResponse:
        tournament = self._get_tournament_in_progress(tournament_id, admin_id)
        match = self._get_playable_match(tournament_id, match_id)
        self._validate_winner(match, winner_id)

        loser_id = match.player2_id if winner_id == match.player1_id else match.player1_id
        new_winner_elo, new_loser_elo = self._apply_elo(winner_id, loser_id, match_id=match.id)

        match.winner_id = winner_id
        uses_score = bool(getattr(tournament, "uses_score", False))
        if uses_score:
            if score_player1 is None or score_player2 is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este torneo requiere score_player1 y score_player2",
                )
            match.score_player1 = score_player1
            match.score_player2 = score_player2
            match.result = f"Score final: {score_player1}-{score_player2}"
            match.score_detail = f"{score_player1}-{score_player2}"
        else:
            match.score_player1 = None
            match.score_player2 = None
            match.result = f"Ganador: jugador {winner_id}"
            match.score_detail = f"winner_id={winner_id}"
        match.status = _STATUS_FINISHED

        tournament_finished = self._advance_by_format(tournament_id, tournament, match, winner_id, loser_id)

        self.audit_repo.record(
            action="REGISTRAR_RESULTADO",
            user_id=admin_id,
            created_at=datetime.now(),
            change_description=f"match_id={match.id},winner_id={winner_id}",
        )
        if tournament_finished:
            tournament.status = _STATUS_FINISHED
            self.audit_repo.record(
                action="FINALIZAR_TORNEO",
                user_id=admin_id,
                created_at=datetime.now(),
                change_description=f"tournament_id={tournament_id}",
            )

        self.match_repo.flush()
        self.match_repo.commit()
        self.match_repo.refresh(match)

        return ResultResponse(
            match=MatchResponse.model_validate(match),
            winner_new_elo=new_winner_elo,
            loser_new_elo=new_loser_elo,
            tournament_finished=tournament_finished,
        )

    def _get_tournament_in_progress(self, tournament_id: int, admin_id: int):
        tournament = self.tournament_repo.get_by_id(tournament_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if tournament.creator_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede registrar resultados",
            )
        if tournament.status != _STATUS_IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en curso",
            )
        return tournament

    def _get_playable_match(self, tournament_id: int, match_id: int) -> MatchModel:
        match = self.match_repo.get_by_id(match_id)
        if match is None or match.tournament_id != tournament_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfrentamiento no encontrado en este torneo")
        if match.status != _STATUS_IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El enfrentamiento no está en curso",
            )
        return match

    @staticmethod
    def _validate_winner(match: MatchModel, winner_id: int) -> None:
        if winner_id not in (match.player1_id, match.player2_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ganador debe ser uno de los participantes del enfrentamiento",
            )

    def _apply_elo(self, winner_id: int, loser_id: int, match_id: int = 0) -> tuple[int, int]:
        winner  = self.player_repo.get_by_id(winner_id)
        loser = self.player_repo.get_by_id(loser_id)
        prev_winner_elo = winner.global_elo
        prev_loser_elo  = loser.global_elo
        new_winner_elo, new_loser_elo = self._compute_new_elo(prev_winner_elo, prev_loser_elo)
        winner.global_elo  = new_winner_elo
        loser.global_elo = new_loser_elo
        self.elo_history_repo.record(winner_id, match_id, prev_winner_elo, new_winner_elo)
        self.elo_history_repo.record(loser_id,  match_id, prev_loser_elo,  new_loser_elo)
        return new_winner_elo, new_loser_elo

    def _advance_by_format(
        self, tournament_id: int, tournament, match: MatchModel, winner_id: int, loser_id: int
    ) -> bool:
        if tournament.elimination_type == _FORMAT_SINGLE:
            return self._advance_winner_single(tournament_id, match) is None
        if tournament.elimination_type == _FORMAT_DOUBLE:
            return self._process_double_result(tournament_id, match, winner_id, loser_id)
        if tournament.elimination_type in _FORMATS_SWISS:
            return self._advance_swiss(tournament_id, tournament, match)
        self.match_repo.flush()
        return self.match_repo.count_active_by_tournament(tournament_id) == 0

    def _advance_swiss(self, tournament_id: int, tournament, match: MatchModel) -> bool:
        self.match_repo.flush()
        current_round = match.round
        if self.match_repo.count_active_by_round(tournament_id, current_round) != 0:
            return False
        next_round = current_round + 1
        if next_round > tournament.rounds:
            return True
        new_matches = self._build_swiss_next_round(tournament_id, next_round)
        self.match_repo.insert_batch(new_matches)
        return False

    @staticmethod
    def _place_in_slot(match: MatchModel, slot: int, player_id: int) -> None:
        if slot == _SLOT_PLAYER1:
            match.player1_id = player_id
        else:
            match.player2_id = player_id
        if match.player1_id is not None and match.player2_id is not None:
            match.status = _STATUS_IN_PROGRESS

    def _advance_winner_single(self, tournament_id: int, match: MatchModel) -> MatchModel | None:
        next_match = self.match_repo.get_by_tournament_round_position(
            tournament_id=tournament_id,
            round=match.round + 1,
            position=match.position // 2,
        )
        if next_match is None:
            return None
        self._place_in_slot(next_match, match.position % 2, match.winner_id)
        return next_match

    def _process_double_result(
        self, tournament_id: int, match: MatchModel, winner_id: int, loser_id: int
    ) -> bool:
        if match.bracket_type == _BRACKET_WINNERS:
            self._advance_winner_double(tournament_id, match, winner_id)
            self._send_loser_to_losers(tournament_id, match, loser_id)
            return False
        if match.bracket_type == _BRACKET_LOSERS:
            self._advance_in_losers(tournament_id, match, winner_id)
            return False
        if match.bracket_type == _BRACKET_GRAND_FINAL:
            return True
        return False

    def _advance_winner_double(self, tournament_id: int, match: MatchModel, winner_id: int) -> None:
        next_match = self.match_repo.get_by_tournament_round_position_bracket(
            tournament_id=tournament_id,
            round=match.round + 1,
            position=match.position // 2,
            bracket_type=_BRACKET_WINNERS,
        )
        if next_match is not None:
            self._place_in_slot(next_match, match.position % 2, winner_id)
        else:
            self._place_in_grand_final(tournament_id, _SLOT_PLAYER1, winner_id)

    def _send_loser_to_losers(self, tournament_id: int, match: MatchModel, loser_id: int) -> None:
        lb_round, lb_pos, lb_slot = self._loser_route_to_losers(match.round, match.position)
        next_match = self.match_repo.get_by_tournament_round_position_bracket(
            tournament_id=tournament_id, round=lb_round, position=lb_pos, bracket_type=_BRACKET_LOSERS,
        )
        if next_match is not None:
            self._place_in_slot(next_match, lb_slot, loser_id)

    def _advance_in_losers(self, tournament_id: int, match: MatchModel, winner_id: int) -> None:
        if match.round % 2 == 1:
            next_pos, next_slot = match.position, _SLOT_PLAYER1
        else:
            next_pos, next_slot = match.position // 2, match.position % 2

        next_match = self.match_repo.get_by_tournament_round_position_bracket(
            tournament_id=tournament_id,
            round=match.round + 1,
            position=next_pos,
            bracket_type=_BRACKET_LOSERS,
        )
        if next_match is not None:
            self._place_in_slot(next_match, next_slot, winner_id)
        else:
            self._place_in_grand_final(tournament_id, _SLOT_PLAYER2, winner_id)

    def _place_in_grand_final(self, tournament_id: int, slot: int, player_id: int) -> None:
        grand_final = self.match_repo.get_by_tournament_round_position_bracket(
            tournament_id=tournament_id, round=1, position=0, bracket_type=_BRACKET_GRAND_FINAL,
        )
        if grand_final is not None:
            self._place_in_slot(grand_final, slot, player_id)

    @staticmethod
    def _loser_route_to_losers(wb_round: int, wb_position: int) -> tuple[int, int, int]:
        if wb_round == 1:
            return 1, wb_position // 2, wb_position % 2
        lb_round = (wb_round - 1) * 2
        return lb_round, wb_position, 1

    @staticmethod
    def _k_factor(elo: int) -> int:
        if elo < _ELO_THRESHOLD_NEW:
            return _ELO_K_NEW
        if elo < _ELO_THRESHOLD_ELITE:
            return _ELO_K_STANDARD
        return _ELO_K_ELITE

    @staticmethod
    def _compute_new_elo(winner_elo: int, loser_elo: int) -> tuple[int, int]:
        expected_winner = _POINTS_WIN / (
            _POINTS_WIN + _ELO_BASE ** ((loser_elo - winner_elo) / _ELO_SCALE)
        )
        k_winner = MatchService._k_factor(winner_elo)
        k_loser  = MatchService._k_factor(loser_elo)
        new_winner_elo  = round(winner_elo + k_winner * (_POINTS_WIN - expected_winner))
        new_loser_elo = round(loser_elo + k_loser * (_POINTS_LOSS - expected_winner))
        return new_winner_elo, new_loser_elo

    @staticmethod
    def _next_power_of_two(n: int) -> int:
        p = 1
        while p < n:
            p <<= 1
        return p

    def _seed_round1_winners(
        self, tournament_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        n = len(participants)
        p = self._next_power_of_two(n)
        bye_count = p - n

        matches: list[MatchModel] = []
        for pos in range(p // 2):
            if pos < bye_count:
                j1_id = participants[pos][0]
                j2_id = None
            else:
                offset = pos - bye_count
                p1_idx = bye_count + offset * 2
                p2_idx = p1_idx + 1
                j1_id = participants[p1_idx][0]
                j2_id = participants[p2_idx][0] if p2_idx < n else None
            matches.append(MatchModel(
                tournament_id=tournament_id, round=1, position=pos,
                bracket_type=_BRACKET_WINNERS,
                player1_id=j1_id, player2_id=j2_id,
                winner_id=None, status=_STATUS_SCHEDULED,
            ))
        return matches

    def _empty_winners_rounds(
        self, tournament_id: int, p: int, start: int, end: int
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        for round in range(start, end + 1):
            for pos in range(p // (2 ** round)):
                matches.append(MatchModel(
                    tournament_id=tournament_id, round=round, position=pos,
                    bracket_type=_BRACKET_WINNERS,
                    player1_id=None, player2_id=None,
                    winner_id=None, status=_STATUS_PENDING,
                ))
        return matches

    def _build_full_bracket(
        self, tournament_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        p = self._next_power_of_two(len(participants))
        total_rounds = p.bit_length() - 1
        return (
            self._seed_round1_winners(tournament_id, participants)
            + self._empty_winners_rounds(tournament_id, p, 2, total_rounds)
        )

    def _build_double_elimination(
        self, tournament_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        p = self._next_power_of_two(len(participants))
        wb_rounds = p.bit_length() - 1
        lb_rounds = (wb_rounds - 1) * 2

        all_matches = self._seed_round1_winners(tournament_id, participants)
        all_matches += self._empty_winners_rounds(tournament_id, p, 2, wb_rounds)

        for round in range(1, lb_rounds + 1):
            k = (round + 1) // 2
            matches_in_round = p // (2 ** (k + 1))
            for pos in range(matches_in_round):
                all_matches.append(MatchModel(
                    tournament_id=tournament_id, round=round, position=pos,
                    bracket_type=_BRACKET_LOSERS,
                    player1_id=None, player2_id=None,
                    winner_id=None, status=_STATUS_PENDING,
                ))

        all_matches.append(MatchModel(
            tournament_id=tournament_id, round=1, position=0,
            bracket_type=_BRACKET_GRAND_FINAL,
            player1_id=None, player2_id=None,
            winner_id=None, status=_STATUS_PENDING,
        ))

        return all_matches

    def _build_round_robin(
        self, tournament_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        n = len(participants)
        pos = 0
        for i in range(n):
            for j in range(i + 1, n):
                matches.append(MatchModel(
                    tournament_id=tournament_id, round=1, position=pos,
                    bracket_type=_BRACKET_WINNERS,
                    player1_id=participants[i][0], player2_id=participants[j][0],
                    winner_id=None, status=_STATUS_SCHEDULED,
                ))
                pos += 1
        return matches

    def _build_swiss_round1(
        self, tournament_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        ordered = sorted(participants, key=lambda x: x[1], reverse=True)
        return self._pair_swiss(tournament_id, round=1, players=[j[0] for j in ordered], played_pairs=set())

    def _build_swiss_next_round(self, tournament_id: int, round: int) -> list[MatchModel]:
        participants = self.tournament_repo.get_confirmed_participants(tournament_id)
        ids = {j[0] for j in participants}

        wins = self.match_repo.get_wins_by_player(tournament_id)
        played_pairs = self.match_repo.get_played_pairs(tournament_id)

        ordered_players = sorted(ids, key=lambda jid: wins.get(jid, 0), reverse=True)
        return self._pair_swiss(tournament_id, round, ordered_players, played_pairs)

    @staticmethod
    def _pair_swiss(
        tournament_id: int, round: int, players: list[int], played_pairs: set[tuple[int, int]]
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        available = list(players)
        pos = 0

        while len(available) >= 2:
            j1 = available.pop(0)
            rival = None
            for i, j2 in enumerate(available):
                pair = (min(j1, j2), max(j1, j2))
                if pair not in played_pairs:
                    rival = available.pop(i)
                    break
            if rival is None:
                rival = available.pop(0)

            matches.append(MatchModel(
                tournament_id=tournament_id, round=round, position=pos,
                bracket_type=_BRACKET_WINNERS,
                player1_id=j1, player2_id=rival,
                winner_id=None, status=_STATUS_IN_PROGRESS,
            ))
            pos += 1

        if available:
            bye_player = available[0]
            matches.append(MatchModel(
                tournament_id=tournament_id, round=round, position=pos,
                bracket_type=_BRACKET_WINNERS,
                player1_id=bye_player, player2_id=None,
                winner_id=bye_player, status=_STATUS_FINISHED,
            ))

        return matches
