from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.match import MatchModel
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.player_repository import PlayerRepository
from app.repositories.match_repository import MatchRepository
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

    def get_ranking(self, torneo_id: int) -> RankingResponse:
        tournament = self.tournament_repo.get_by_id(torneo_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")

        participants = self.tournament_repo.get_confirmed_participants(torneo_id)
        wins = self.match_repo.get_wins_by_player(torneo_id)

        entries = sorted(
            [{"player_id": jid, "wins": wins.get(jid, 0), "elo_global": elo} for jid, elo in participants],
            key=lambda e: (-e["wins"], -e["elo_global"]),
        )

        ranking = [
            RankingEntry(posicion=i + 1, jugador_id=e["player_id"], wins=e["wins"], elo_global=e["elo_global"])
            for i, e in enumerate(entries)
        ]
        return RankingResponse(torneo_id=torneo_id, tipo_eliminacion=tournament.tipo_eliminacion, estado=tournament.estado, ranking=ranking)

    def get_player_history(self, torneo_id: int, jugador_id: int) -> list[MatchResponse]:
        tournament = self.tournament_repo.get_by_id(torneo_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        matches = self.match_repo.get_player_history(torneo_id, jugador_id)
        return [MatchResponse.model_validate(m) for m in matches]

    def get_bracket(self, torneo_id: int) -> BracketResponse:
        tournament = self.tournament_repo.get_by_id(torneo_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        matches = self.match_repo.get_by_tournament(torneo_id)
        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=tournament.estado,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def generate_bracket(self, torneo_id: int, admin_id: int) -> BracketResponse:
        tournament = self.tournament_repo.get_by_id(torneo_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if tournament.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador del torneo puede generar el cuadro de enfrentamiento",
            )
        if tournament.estado != _STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El periodo de inscripciones no está cerrado o el torneo ya fue procesado",
            )

        participants = self.tournament_repo.get_confirmed_participants(torneo_id)
        min_req = _MIN_PARTICIPANTS.get(tournament.tipo_eliminacion, 2)
        if len(participants) < min_req:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Se requieren al menos {min_req} participantes confirmados para {tournament.tipo_eliminacion}",
            )

        match_models = self._build_match_models(tournament, torneo_id, participants)

        match_models = self.match_repo.insert_batch(match_models)
        match_responses = [MatchResponse.model_validate(m) for m in match_models]

        self.audit_repo.record(accion="GENERAR_BRACKET", usuario_id=admin_id, fecha=datetime.now())
        tournament = self.tournament_repo.update_status(tournament, _STATUS_READY_TO_START)
        return BracketResponse(torneo_id=torneo_id, estado_torneo=tournament.estado, matches=match_responses)

    def _build_match_models(
        self, tournament, torneo_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        if tournament.tipo_eliminacion == _FORMAT_SINGLE:
            return self._build_full_bracket(torneo_id, participants)
        if tournament.tipo_eliminacion == _FORMAT_DOUBLE:
            return self._build_double_elimination(torneo_id, participants)
        if tournament.tipo_eliminacion in _FORMATS_ROUND_ROBIN:
            return self._build_round_robin(torneo_id, participants)
        if tournament.tipo_eliminacion in _FORMATS_SWISS:
            return self._build_swiss_round1(torneo_id, participants)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El formato '{tournament.tipo_eliminacion}' no tiene generación de bracket implementada",
        )

    def start_tournament(self, torneo_id: int, admin_id: int) -> BracketResponse:
        tournament = self.tournament_repo.get_by_id(torneo_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if tournament.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede iniciar el torneo",
            )
        if tournament.estado != _STATUS_READY_TO_START:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en estado 'Listo para iniciar'",
            )

        if tournament.tipo_eliminacion in _FORMATS_WITH_BRACKET:
            self._activate_round1_with_bracket(torneo_id)
        else:
            for m in self.match_repo.get_by_tournament(torneo_id):
                m.estado = _STATUS_IN_PROGRESS

        tournament.estado = _STATUS_IN_PROGRESS
        self.audit_repo.record(accion="INICIAR_TORNEO", usuario_id=admin_id, fecha=datetime.now())
        self.match_repo.flush()
        self.match_repo.commit()
        self.match_repo.refresh(tournament)

        matches = self.match_repo.get_by_tournament(torneo_id)
        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=tournament.estado,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def _activate_round1_with_bracket(self, torneo_id: int) -> None:
        for bye in self.match_repo.get_round1_byes(torneo_id):
            bye.ganador_id = bye.jugador1_id
            bye.estado = _STATUS_FINISHED
            self._advance_winner_single(torneo_id, bye)
        for m in self.match_repo.get_by_tournament_round(torneo_id, ronda=1):
            if m.jugador2_id is not None and m.estado != _STATUS_FINISHED:
                m.estado = _STATUS_IN_PROGRESS

    def record_result(
        self, torneo_id: int, match_id: int, winner_id: int, admin_id: int
    ) -> ResultResponse:
        tournament = self._get_tournament_in_progress(torneo_id, admin_id)
        match = self._get_playable_match(torneo_id, match_id)
        self._validate_winner(match, winner_id)

        loser_id = match.jugador2_id if winner_id == match.jugador1_id else match.jugador1_id
        new_winner_elo, new_loser_elo = self._apply_elo(winner_id, loser_id)

        match.ganador_id = winner_id
        match.estado = _STATUS_FINISHED

        tournament_finished = self._advance_by_format(torneo_id, tournament, match, winner_id, loser_id)

        self.audit_repo.record(accion="REGISTRAR_RESULTADO", usuario_id=admin_id, fecha=datetime.now())
        if tournament_finished:
            tournament.estado = _STATUS_FINISHED
            self.audit_repo.record(accion="FINALIZAR_TORNEO", usuario_id=admin_id, fecha=datetime.now())

        self.match_repo.flush()
        self.match_repo.commit()
        self.match_repo.refresh(match)

        return ResultResponse(
            match=MatchResponse.model_validate(match),
            ganador_nuevo_elo=new_winner_elo,
            perdedor_nuevo_elo=new_loser_elo,
            torneo_finalizado=tournament_finished,
        )

    def _get_tournament_in_progress(self, torneo_id: int, admin_id: int):
        tournament = self.tournament_repo.get_by_id(torneo_id)
        if tournament is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if tournament.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede registrar resultados",
            )
        if tournament.estado != _STATUS_IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en curso",
            )
        return tournament

    def _get_playable_match(self, torneo_id: int, match_id: int) -> MatchModel:
        match = self.match_repo.get_by_id(match_id)
        if match is None or match.torneo_id != torneo_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfrentamiento no encontrado en este torneo")
        if match.estado != _STATUS_IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El enfrentamiento no está en curso",
            )
        return match

    @staticmethod
    def _validate_winner(match: MatchModel, winner_id: int) -> None:
        if winner_id not in (match.jugador1_id, match.jugador2_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ganador debe ser uno de los participantes del enfrentamiento",
            )

    def _apply_elo(self, winner_id: int, loser_id: int) -> tuple[int, int]:
        winner  = self.player_repo.get_by_id(winner_id)
        loser = self.player_repo.get_by_id(loser_id)
        new_winner_elo, new_loser_elo = self._compute_new_elo(winner.elo_global, loser.elo_global)
        winner.elo_global  = new_winner_elo
        loser.elo_global = new_loser_elo
        return new_winner_elo, new_loser_elo

    def _advance_by_format(
        self, torneo_id: int, tournament, match: MatchModel, winner_id: int, loser_id: int
    ) -> bool:
        if tournament.tipo_eliminacion == _FORMAT_SINGLE:
            return self._advance_winner_single(torneo_id, match) is None
        if tournament.tipo_eliminacion == _FORMAT_DOUBLE:
            return self._process_double_result(torneo_id, match, winner_id, loser_id)
        if tournament.tipo_eliminacion in _FORMATS_SWISS:
            return self._advance_swiss(torneo_id, tournament, match)
        self.match_repo.flush()
        return self.match_repo.count_active_by_tournament(torneo_id) == 0

    def _advance_swiss(self, torneo_id: int, tournament, match: MatchModel) -> bool:
        self.match_repo.flush()
        current_round = match.ronda
        if self.match_repo.count_active_by_round(torneo_id, current_round) != 0:
            return False
        next_round = current_round + 1
        if next_round > tournament.rondas:
            return True
        new_matches = self._build_swiss_next_round(torneo_id, next_round)
        self.match_repo.insert_batch(new_matches)
        return False

    @staticmethod
    def _place_in_slot(match: MatchModel, slot: int, jugador_id: int) -> None:
        if slot == _SLOT_PLAYER1:
            match.jugador1_id = jugador_id
        else:
            match.jugador2_id = jugador_id
        if match.jugador1_id is not None and match.jugador2_id is not None:
            match.estado = _STATUS_IN_PROGRESS

    def _advance_winner_single(self, torneo_id: int, match: MatchModel) -> MatchModel | None:
        next_match = self.match_repo.get_by_tournament_round_position(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=match.posicion // 2,
        )
        if next_match is None:
            return None
        self._place_in_slot(next_match, match.posicion % 2, match.ganador_id)
        return next_match

    def _process_double_result(
        self, torneo_id: int, match: MatchModel, winner_id: int, loser_id: int
    ) -> bool:
        if match.bracket_tipo == _BRACKET_WINNERS:
            self._advance_winner_double(torneo_id, match, winner_id)
            self._send_loser_to_losers(torneo_id, match, loser_id)
            return False
        if match.bracket_tipo == _BRACKET_LOSERS:
            self._advance_in_losers(torneo_id, match, winner_id)
            return False
        if match.bracket_tipo == _BRACKET_GRAND_FINAL:
            return True
        return False

    def _advance_winner_double(self, torneo_id: int, match: MatchModel, winner_id: int) -> None:
        next_match = self.match_repo.get_by_tournament_round_position_bracket(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=match.posicion // 2,
            bracket_tipo=_BRACKET_WINNERS,
        )
        if next_match is not None:
            self._place_in_slot(next_match, match.posicion % 2, winner_id)
        else:
            self._place_in_grand_final(torneo_id, _SLOT_PLAYER1, winner_id)

    def _send_loser_to_losers(self, torneo_id: int, match: MatchModel, loser_id: int) -> None:
        lb_round, lb_pos, lb_slot = self._loser_route_to_losers(match.ronda, match.posicion)
        next_match = self.match_repo.get_by_tournament_round_position_bracket(
            torneo_id=torneo_id, ronda=lb_round, posicion=lb_pos, bracket_tipo=_BRACKET_LOSERS,
        )
        if next_match is not None:
            self._place_in_slot(next_match, lb_slot, loser_id)

    def _advance_in_losers(self, torneo_id: int, match: MatchModel, winner_id: int) -> None:
        if match.ronda % 2 == 1:
            next_pos, next_slot = match.posicion, _SLOT_PLAYER1
        else:
            next_pos, next_slot = match.posicion // 2, match.posicion % 2

        next_match = self.match_repo.get_by_tournament_round_position_bracket(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=next_pos,
            bracket_tipo=_BRACKET_LOSERS,
        )
        if next_match is not None:
            self._place_in_slot(next_match, next_slot, winner_id)
        else:
            self._place_in_grand_final(torneo_id, _SLOT_PLAYER2, winner_id)

    def _place_in_grand_final(self, torneo_id: int, slot: int, jugador_id: int) -> None:
        grand_final = self.match_repo.get_by_tournament_round_position_bracket(
            torneo_id=torneo_id, ronda=1, posicion=0, bracket_tipo=_BRACKET_GRAND_FINAL,
        )
        if grand_final is not None:
            self._place_in_slot(grand_final, slot, jugador_id)

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
        self, torneo_id: int, participants: list[tuple[int, int]]
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
                torneo_id=torneo_id, ronda=1, posicion=pos,
                bracket_tipo=_BRACKET_WINNERS,
                jugador1_id=j1_id, jugador2_id=j2_id,
                ganador_id=None, estado=_STATUS_SCHEDULED,
            ))
        return matches

    def _empty_winners_rounds(
        self, torneo_id: int, p: int, start: int, end: int
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        for ronda in range(start, end + 1):
            for pos in range(p // (2 ** ronda)):
                matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=ronda, posicion=pos,
                    bracket_tipo=_BRACKET_WINNERS,
                    jugador1_id=None, jugador2_id=None,
                    ganador_id=None, estado=_STATUS_PENDING,
                ))
        return matches

    def _build_full_bracket(
        self, torneo_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        p = self._next_power_of_two(len(participants))
        total_rounds = p.bit_length() - 1
        return (
            self._seed_round1_winners(torneo_id, participants)
            + self._empty_winners_rounds(torneo_id, p, 2, total_rounds)
        )

    def _build_double_elimination(
        self, torneo_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        p = self._next_power_of_two(len(participants))
        wb_rounds = p.bit_length() - 1
        lb_rounds = (wb_rounds - 1) * 2

        all_matches = self._seed_round1_winners(torneo_id, participants)
        all_matches += self._empty_winners_rounds(torneo_id, p, 2, wb_rounds)

        for ronda in range(1, lb_rounds + 1):
            k = (ronda + 1) // 2
            matches_in_round = p // (2 ** (k + 1))
            for pos in range(matches_in_round):
                all_matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=ronda, posicion=pos,
                    bracket_tipo=_BRACKET_LOSERS,
                    jugador1_id=None, jugador2_id=None,
                    ganador_id=None, estado=_STATUS_PENDING,
                ))

        all_matches.append(MatchModel(
            torneo_id=torneo_id, ronda=1, posicion=0,
            bracket_tipo=_BRACKET_GRAND_FINAL,
            jugador1_id=None, jugador2_id=None,
            ganador_id=None, estado=_STATUS_PENDING,
        ))

        return all_matches

    def _build_round_robin(
        self, torneo_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        n = len(participants)
        pos = 0
        for i in range(n):
            for j in range(i + 1, n):
                matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=1, posicion=pos,
                    bracket_tipo=_BRACKET_WINNERS,
                    jugador1_id=participants[i][0], jugador2_id=participants[j][0],
                    ganador_id=None, estado=_STATUS_SCHEDULED,
                ))
                pos += 1
        return matches

    def _build_swiss_round1(
        self, torneo_id: int, participants: list[tuple[int, int]]
    ) -> list[MatchModel]:
        ordered = sorted(participants, key=lambda x: x[1], reverse=True)
        return self._pair_swiss(torneo_id, ronda=1, players=[j[0] for j in ordered], played_pairs=set())

    def _build_swiss_next_round(self, torneo_id: int, ronda: int) -> list[MatchModel]:
        participants = self.tournament_repo.get_confirmed_participants(torneo_id)
        ids = {j[0] for j in participants}

        wins = self.match_repo.get_wins_by_player(torneo_id)
        played_pairs = self.match_repo.get_played_pairs(torneo_id)

        ordered_players = sorted(ids, key=lambda jid: wins.get(jid, 0), reverse=True)
        return self._pair_swiss(torneo_id, ronda, ordered_players, played_pairs)

    @staticmethod
    def _pair_swiss(
        torneo_id: int, ronda: int, players: list[int], played_pairs: set[tuple[int, int]]
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
                torneo_id=torneo_id, ronda=ronda, posicion=pos,
                bracket_tipo=_BRACKET_WINNERS,
                jugador1_id=j1, jugador2_id=rival,
                ganador_id=None, estado=_STATUS_IN_PROGRESS,
            ))
            pos += 1

        if available:
            bye_player = available[0]
            matches.append(MatchModel(
                torneo_id=torneo_id, ronda=ronda, posicion=pos,
                bracket_tipo=_BRACKET_WINNERS,
                jugador1_id=bye_player, jugador2_id=None,
                ganador_id=bye_player, estado=_STATUS_FINISHED,
            ))

        return matches
