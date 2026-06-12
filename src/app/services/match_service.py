from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.match import MatchModel
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.jugador_repository import JugadorRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.match import MatchResponse, ResultadoResponse
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
        self.torneo_repo  = TournamentRepository(db)
        self.match_repo   = MatchRepository(db)
        self.jugador_repo = JugadorRepository(db)
        self.audit_repo   = AuditLogRepository(db)

    def get_ranking(self, torneo_id: int) -> RankingResponse:
        torneo = self.torneo_repo.get_by_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")

        participantes = self.torneo_repo.get_confirmed_participants(torneo_id)
        victorias = self.match_repo.get_wins_by_player(torneo_id)

        entradas = sorted(
            [{"jugador_id": jid, "victorias": victorias.get(jid, 0), "elo_global": elo} for jid, elo in participantes],
            key=lambda e: (-e["victorias"], -e["elo_global"]),
        )

        ranking = [
            RankingEntry(posicion=i + 1, jugador_id=e["jugador_id"], victorias=e["victorias"], elo_global=e["elo_global"])
            for i, e in enumerate(entradas)
        ]
        return RankingResponse(torneo_id=torneo_id, tipo_eliminacion=torneo.tipo_eliminacion, estado=torneo.estado, ranking=ranking)

    def get_player_history(self, torneo_id: int, jugador_id: int) -> list[MatchResponse]:
        torneo = self.torneo_repo.get_by_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        matches = self.match_repo.get_player_history(torneo_id, jugador_id)
        return [MatchResponse.model_validate(m) for m in matches]

    def get_bracket(self, torneo_id: int) -> BracketResponse:
        torneo = self.torneo_repo.get_by_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        matches = self.match_repo.get_by_tournament(torneo_id)
        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=torneo.estado,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def generate_bracket(self, torneo_id: int, admin_id: int) -> BracketResponse:
        torneo = self.torneo_repo.get_by_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador del torneo puede generar el cuadro de enfrentamiento",
            )
        if torneo.estado != _STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El periodo de inscripciones no está cerrado o el torneo ya fue procesado",
            )

        participantes = self.torneo_repo.get_confirmed_participants(torneo_id)
        min_req = _MIN_PARTICIPANTS.get(torneo.tipo_eliminacion, 2)
        if len(participantes) < min_req:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Se requieren al menos {min_req} participantes confirmados para {torneo.tipo_eliminacion}",
            )

        match_models = self._build_match_models(torneo, torneo_id, participantes)

        match_models = self.match_repo.insert_batch(match_models)
        match_responses = [MatchResponse.model_validate(m) for m in match_models]

        self.audit_repo.record(accion="GENERAR_BRACKET", usuario_id=admin_id, fecha=datetime.now())
        torneo = self.torneo_repo.update_status(torneo, _STATUS_READY_TO_START)
        return BracketResponse(torneo_id=torneo_id, estado_torneo=torneo.estado, matches=match_responses)

    def _build_match_models(
        self, torneo, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        if torneo.tipo_eliminacion == _FORMAT_SINGLE:
            return self._build_full_bracket(torneo_id, participantes)
        if torneo.tipo_eliminacion == _FORMAT_DOUBLE:
            return self._build_double_elimination(torneo_id, participantes)
        if torneo.tipo_eliminacion in _FORMATS_ROUND_ROBIN:
            return self._build_round_robin(torneo_id, participantes)
        if torneo.tipo_eliminacion in _FORMATS_SWISS:
            return self._build_swiss_round1(torneo_id, participantes)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El formato '{torneo.tipo_eliminacion}' no tiene generación de bracket implementada",
        )

    def start_tournament(self, torneo_id: int, admin_id: int) -> BracketResponse:
        torneo = self.torneo_repo.get_by_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede iniciar el torneo",
            )
        if torneo.estado != _STATUS_READY_TO_START:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en estado 'Listo para iniciar'",
            )

        if torneo.tipo_eliminacion in _FORMATS_WITH_BRACKET:
            self._activate_round1_with_bracket(torneo_id)
        else:
            for m in self.match_repo.get_by_tournament(torneo_id):
                m.estado = _STATUS_IN_PROGRESS

        torneo.estado = _STATUS_IN_PROGRESS
        self.audit_repo.record(accion="INICIAR_TORNEO", usuario_id=admin_id, fecha=datetime.now())
        self.match_repo.flush()
        self.match_repo.commit()
        self.match_repo.refresh(torneo)

        matches = self.match_repo.get_by_tournament(torneo_id)
        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=torneo.estado,
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
        self, torneo_id: int, match_id: int, ganador_id: int, admin_id: int
    ) -> ResultadoResponse:
        torneo = self._get_tournament_in_progress(torneo_id, admin_id)
        match = self._get_playable_match(torneo_id, match_id)
        self._validate_winner(match, ganador_id)

        perdedor_id = match.jugador2_id if ganador_id == match.jugador1_id else match.jugador1_id
        nuevo_elo_g, nuevo_elo_p = self._apply_elo(ganador_id, perdedor_id)

        match.ganador_id = ganador_id
        match.estado = _STATUS_FINISHED

        torneo_finalizado = self._advance_by_format(torneo_id, torneo, match, ganador_id, perdedor_id)

        self.audit_repo.record(accion="REGISTRAR_RESULTADO", usuario_id=admin_id, fecha=datetime.now())
        if torneo_finalizado:
            torneo.estado = _STATUS_FINISHED
            self.audit_repo.record(accion="FINALIZAR_TORNEO", usuario_id=admin_id, fecha=datetime.now())

        self.match_repo.flush()
        self.match_repo.commit()
        self.match_repo.refresh(match)

        return ResultadoResponse(
            match=MatchResponse.model_validate(match),
            ganador_nuevo_elo=nuevo_elo_g,
            perdedor_nuevo_elo=nuevo_elo_p,
            torneo_finalizado=torneo_finalizado,
        )

    def _get_tournament_in_progress(self, torneo_id: int, admin_id: int):
        torneo = self.torneo_repo.get_by_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede registrar resultados",
            )
        if torneo.estado != _STATUS_IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en curso",
            )
        return torneo

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
    def _validate_winner(match: MatchModel, ganador_id: int) -> None:
        if ganador_id not in (match.jugador1_id, match.jugador2_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ganador debe ser uno de los participantes del enfrentamiento",
            )

    def _apply_elo(self, ganador_id: int, perdedor_id: int) -> tuple[int, int]:
        ganador_obj  = self.jugador_repo.get_by_id(ganador_id)
        perdedor_obj = self.jugador_repo.get_by_id(perdedor_id)
        nuevo_elo_g, nuevo_elo_p = self._compute_new_elo(ganador_obj.elo_global, perdedor_obj.elo_global)
        ganador_obj.elo_global  = nuevo_elo_g
        perdedor_obj.elo_global = nuevo_elo_p
        return nuevo_elo_g, nuevo_elo_p

    def _advance_by_format(
        self, torneo_id: int, torneo, match: MatchModel, ganador_id: int, perdedor_id: int
    ) -> bool:
        if torneo.tipo_eliminacion == _FORMAT_SINGLE:
            return self._advance_winner_single(torneo_id, match) is None
        if torneo.tipo_eliminacion == _FORMAT_DOUBLE:
            return self._process_double_result(torneo_id, match, ganador_id, perdedor_id)
        if torneo.tipo_eliminacion in _FORMATS_SWISS:
            return self._advance_swiss(torneo_id, torneo, match)
        self.match_repo.flush()
        return self.match_repo.count_active_by_tournament(torneo_id) == 0

    def _advance_swiss(self, torneo_id: int, torneo, match: MatchModel) -> bool:
        self.match_repo.flush()
        ronda_actual = match.ronda
        if self.match_repo.count_active_by_round(torneo_id, ronda_actual) != 0:
            return False
        ronda_siguiente = ronda_actual + 1
        if ronda_siguiente > torneo.rondas:
            return True
        nuevos = self._build_swiss_next_round(torneo_id, ronda_siguiente)
        self.match_repo.insert_batch(nuevos)
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
        siguiente = self.match_repo.get_by_tournament_round_position(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=match.posicion // 2,
        )
        if siguiente is None:
            return None
        self._place_in_slot(siguiente, match.posicion % 2, match.ganador_id)
        return siguiente

    def _process_double_result(
        self, torneo_id: int, match: MatchModel, ganador_id: int, perdedor_id: int
    ) -> bool:
        if match.bracket_tipo == _BRACKET_WINNERS:
            self._advance_winner_double(torneo_id, match, ganador_id)
            self._send_loser_to_losers(torneo_id, match, perdedor_id)
            return False
        if match.bracket_tipo == _BRACKET_LOSERS:
            self._advance_in_losers(torneo_id, match, ganador_id)
            return False
        if match.bracket_tipo == _BRACKET_GRAND_FINAL:
            return True
        return False

    def _advance_winner_double(self, torneo_id: int, match: MatchModel, ganador_id: int) -> None:
        siguiente = self.match_repo.get_by_tournament_round_position_bracket(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=match.posicion // 2,
            bracket_tipo=_BRACKET_WINNERS,
        )
        if siguiente is not None:
            self._place_in_slot(siguiente, match.posicion % 2, ganador_id)
        else:
            self._place_in_grand_final(torneo_id, _SLOT_PLAYER1, ganador_id)

    def _send_loser_to_losers(self, torneo_id: int, match: MatchModel, perdedor_id: int) -> None:
        lb_ronda, lb_pos, lb_slot = self._loser_route_to_losers(match.ronda, match.posicion)
        siguiente = self.match_repo.get_by_tournament_round_position_bracket(
            torneo_id=torneo_id, ronda=lb_ronda, posicion=lb_pos, bracket_tipo=_BRACKET_LOSERS,
        )
        if siguiente is not None:
            self._place_in_slot(siguiente, lb_slot, perdedor_id)

    def _advance_in_losers(self, torneo_id: int, match: MatchModel, ganador_id: int) -> None:
        if match.ronda % 2 == 1:
            next_pos, next_slot = match.posicion, _SLOT_PLAYER1
        else:
            next_pos, next_slot = match.posicion // 2, match.posicion % 2

        siguiente = self.match_repo.get_by_tournament_round_position_bracket(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=next_pos,
            bracket_tipo=_BRACKET_LOSERS,
        )
        if siguiente is not None:
            self._place_in_slot(siguiente, next_slot, ganador_id)
        else:
            self._place_in_grand_final(torneo_id, _SLOT_PLAYER2, ganador_id)

    def _place_in_grand_final(self, torneo_id: int, slot: int, jugador_id: int) -> None:
        gran_final = self.match_repo.get_by_tournament_round_position_bracket(
            torneo_id=torneo_id, ronda=1, posicion=0, bracket_tipo=_BRACKET_GRAND_FINAL,
        )
        if gran_final is not None:
            self._place_in_slot(gran_final, slot, jugador_id)

    @staticmethod
    def _loser_route_to_losers(wb_ronda: int, wb_posicion: int) -> tuple[int, int, int]:
        if wb_ronda == 1:
            return 1, wb_posicion // 2, wb_posicion % 2
        lb_ronda = (wb_ronda - 1) * 2
        return lb_ronda, wb_posicion, 1

    @staticmethod
    def _k_factor(elo: int) -> int:
        if elo < _ELO_THRESHOLD_NEW:
            return _ELO_K_NEW
        if elo < _ELO_THRESHOLD_ELITE:
            return _ELO_K_STANDARD
        return _ELO_K_ELITE

    @staticmethod
    def _compute_new_elo(elo_ganador: int, elo_perdedor: int) -> tuple[int, int]:
        expected_winner = _POINTS_WIN / (
            _POINTS_WIN + _ELO_BASE ** ((elo_perdedor - elo_ganador) / _ELO_SCALE)
        )
        k_winner = MatchService._k_factor(elo_ganador)
        k_loser  = MatchService._k_factor(elo_perdedor)
        nuevo_ganador  = round(elo_ganador + k_winner * (_POINTS_WIN - expected_winner))
        nuevo_perdedor = round(elo_perdedor + k_loser * (_POINTS_LOSS - expected_winner))
        return nuevo_ganador, nuevo_perdedor

    @staticmethod
    def _next_power_of_two(n: int) -> int:
        p = 1
        while p < n:
            p <<= 1
        return p

    def _seed_round1_winners(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        n = len(participantes)
        p = self._next_power_of_two(n)
        bye_count = p - n

        matches: list[MatchModel] = []
        for pos in range(p // 2):
            if pos < bye_count:
                j1_id = participantes[pos][0]
                j2_id = None
            else:
                offset = pos - bye_count
                p1_idx = bye_count + offset * 2
                p2_idx = p1_idx + 1
                j1_id = participantes[p1_idx][0]
                j2_id = participantes[p2_idx][0] if p2_idx < n else None
            matches.append(MatchModel(
                torneo_id=torneo_id, ronda=1, posicion=pos,
                bracket_tipo=_BRACKET_WINNERS,
                jugador1_id=j1_id, jugador2_id=j2_id,
                ganador_id=None, estado=_STATUS_SCHEDULED,
            ))
        return matches

    def _empty_winners_rounds(
        self, torneo_id: int, p: int, desde: int, hasta: int
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        for ronda in range(desde, hasta + 1):
            for pos in range(p // (2 ** ronda)):
                matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=ronda, posicion=pos,
                    bracket_tipo=_BRACKET_WINNERS,
                    jugador1_id=None, jugador2_id=None,
                    ganador_id=None, estado=_STATUS_PENDING,
                ))
        return matches

    def _build_full_bracket(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        p = self._next_power_of_two(len(participantes))
        total_rondas = p.bit_length() - 1
        return (
            self._seed_round1_winners(torneo_id, participantes)
            + self._empty_winners_rounds(torneo_id, p, 2, total_rondas)
        )

    def _build_double_elimination(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        p = self._next_power_of_two(len(participantes))
        wb_rondas = p.bit_length() - 1
        lb_rondas = (wb_rondas - 1) * 2

        all_matches = self._seed_round1_winners(torneo_id, participantes)
        all_matches += self._empty_winners_rounds(torneo_id, p, 2, wb_rondas)

        for ronda in range(1, lb_rondas + 1):
            k = (ronda + 1) // 2
            matches_en_ronda = p // (2 ** (k + 1))
            for pos in range(matches_en_ronda):
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
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        n = len(participantes)
        pos = 0
        for i in range(n):
            for j in range(i + 1, n):
                matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=1, posicion=pos,
                    bracket_tipo=_BRACKET_WINNERS,
                    jugador1_id=participantes[i][0], jugador2_id=participantes[j][0],
                    ganador_id=None, estado=_STATUS_SCHEDULED,
                ))
                pos += 1
        return matches

    def _build_swiss_round1(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        ordenados = sorted(participantes, key=lambda x: x[1], reverse=True)
        return self._pair_swiss(torneo_id, ronda=1, jugadores=[j[0] for j in ordenados], pares_jugados=set())

    def _build_swiss_next_round(self, torneo_id: int, ronda: int) -> list[MatchModel]:
        participantes = self.torneo_repo.get_confirmed_participants(torneo_id)
        ids = {j[0] for j in participantes}

        victorias = self.match_repo.get_wins_by_player(torneo_id)
        pares_jugados = self.match_repo.get_played_pairs(torneo_id)

        jugadores_ordenados = sorted(ids, key=lambda jid: victorias.get(jid, 0), reverse=True)
        return self._pair_swiss(torneo_id, ronda, jugadores_ordenados, pares_jugados)

    @staticmethod
    def _pair_swiss(
        torneo_id: int, ronda: int, jugadores: list[int], pares_jugados: set[tuple[int, int]]
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        disponibles = list(jugadores)
        pos = 0

        while len(disponibles) >= 2:
            j1 = disponibles.pop(0)
            rival = None
            for i, j2 in enumerate(disponibles):
                par = (min(j1, j2), max(j1, j2))
                if par not in pares_jugados:
                    rival = disponibles.pop(i)
                    break
            if rival is None:
                rival = disponibles.pop(0)

            matches.append(MatchModel(
                torneo_id=torneo_id, ronda=ronda, posicion=pos,
                bracket_tipo=_BRACKET_WINNERS,
                jugador1_id=j1, jugador2_id=rival,
                ganador_id=None, estado=_STATUS_IN_PROGRESS,
            ))
            pos += 1

        if disponibles:
            bye_jugador = disponibles[0]
            matches.append(MatchModel(
                torneo_id=torneo_id, ronda=ronda, posicion=pos,
                bracket_tipo=_BRACKET_WINNERS,
                jugador1_id=bye_jugador, jugador2_id=None,
                ganador_id=bye_jugador, estado=_STATUS_FINISHED,
            ))

        return matches
