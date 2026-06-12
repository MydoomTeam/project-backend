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

_ELO_ESCALA = 400
_ELO_BASE = 10.0
_PUNTOS_VICTORIA = 1.0
_PUNTOS_DERROTA = 0.0

_ELO_K_NUEVO    = 40
_ELO_K_ESTANDAR = 32
_ELO_K_ELITE    = 16
_ELO_UMBRAL_NUEVO  = 1000
_ELO_UMBRAL_ELITE  = 2000

_MIN_PARTICIPANTES: dict[str, int] = {
    "Eliminación Sencilla": 2,
    "Eliminación Doble":    4,
    "Round Robin":          3,
    "Swiss":                4,
}

_BRACKET_GANADORES = "ganadores"
_BRACKET_PERDEDORES = "perdedores"
_BRACKET_GRAN_FINAL = "gran_final"

_FORMATO_SENCILLA = "Eliminación Sencilla"
_FORMATO_DOBLE    = "Eliminación Doble"
_FORMATOS_CON_BRACKET    = {_FORMATO_SENCILLA, _FORMATO_DOBLE}
_FORMATOS_TODOS_VS_TODOS = {"Round Robin"}
_FORMATOS_SWISS          = {"Swiss"}

_ESTADO_PENDIENTE = "Pendiente"
_ESTADO_PROGRAMADO = "Programado"
_ESTADO_EN_CURSO = "En curso"
_ESTADO_FINALIZADO = "Finalizado"
_ESTADO_LISTO_PARA_INICIAR = "Listo para iniciar"

_SLOT_JUGADOR1 = 0
_SLOT_JUGADOR2 = 1


class MatchService:
    def __init__(self, db: Session):
        self.torneo_repo  = TournamentRepository(db)
        self.match_repo   = MatchRepository(db)
        self.jugador_repo = JugadorRepository(db)
        self.audit_repo   = AuditLogRepository(db)

    def obtener_ranking(self, torneo_id: int) -> RankingResponse:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")

        participantes = self.torneo_repo.obtener_participantes_confirmados(torneo_id)
        victorias = self.match_repo.obtener_victorias_por_jugador(torneo_id)

        entradas = sorted(
            [{"jugador_id": jid, "victorias": victorias.get(jid, 0), "elo_global": elo} for jid, elo in participantes],
            key=lambda e: (-e["victorias"], -e["elo_global"]),
        )

        ranking = [
            RankingEntry(posicion=i + 1, jugador_id=e["jugador_id"], victorias=e["victorias"], elo_global=e["elo_global"])
            for i, e in enumerate(entradas)
        ]
        return RankingResponse(torneo_id=torneo_id, tipo_eliminacion=torneo.tipo_eliminacion, estado=torneo.estado, ranking=ranking)

    def obtener_historial_jugador(self, torneo_id: int, jugador_id: int) -> list[MatchResponse]:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        matches = self.match_repo.obtener_historial_jugador(torneo_id, jugador_id)
        return [MatchResponse.model_validate(m) for m in matches]

    def obtener_bracket(self, torneo_id: int) -> BracketResponse:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        matches = self.match_repo.obtener_por_torneo(torneo_id)
        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=torneo.estado,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def generar_bracket(self, torneo_id: int, admin_id: int) -> BracketResponse:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador del torneo puede generar el cuadro de enfrentamiento",
            )
        if torneo.estado != _ESTADO_PENDIENTE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El periodo de inscripciones no está cerrado o el torneo ya fue procesado",
            )

        participantes = self.torneo_repo.obtener_participantes_confirmados(torneo_id)
        min_req = _MIN_PARTICIPANTES.get(torneo.tipo_eliminacion, 2)
        if len(participantes) < min_req:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Se requieren al menos {min_req} participantes confirmados para {torneo.tipo_eliminacion}",
            )

        match_models = self._construir_match_models(torneo, torneo_id, participantes)

        match_models = self.match_repo.insertar_en_lote(match_models)
        match_responses = [MatchResponse.model_validate(m) for m in match_models]

        self.audit_repo.record(accion="GENERAR_BRACKET", usuario_id=admin_id, fecha=datetime.now())
        torneo = self.torneo_repo.actualizar_estado(torneo, _ESTADO_LISTO_PARA_INICIAR)
        return BracketResponse(torneo_id=torneo_id, estado_torneo=torneo.estado, matches=match_responses)

    def _construir_match_models(
        self, torneo, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        if torneo.tipo_eliminacion == _FORMATO_SENCILLA:
            return self._construir_bracket_completo(torneo_id, participantes)
        if torneo.tipo_eliminacion == _FORMATO_DOBLE:
            return self._construir_eliminacion_doble(torneo_id, participantes)
        if torneo.tipo_eliminacion in _FORMATOS_TODOS_VS_TODOS:
            return self._construir_round_robin(torneo_id, participantes)
        if torneo.tipo_eliminacion in _FORMATOS_SWISS:
            return self._construir_swiss_ronda1(torneo_id, participantes)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El formato '{torneo.tipo_eliminacion}' no tiene generación de bracket implementada",
        )

    def iniciar_torneo(self, torneo_id: int, admin_id: int) -> BracketResponse:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede iniciar el torneo",
            )
        if torneo.estado != _ESTADO_LISTO_PARA_INICIAR:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en estado 'Listo para iniciar'",
            )

        if torneo.tipo_eliminacion in _FORMATOS_CON_BRACKET:
            self._activar_ronda1_con_bracket(torneo_id)
        else:
            for m in self.match_repo.obtener_por_torneo(torneo_id):
                m.estado = _ESTADO_EN_CURSO

        torneo.estado = _ESTADO_EN_CURSO
        self.audit_repo.record(accion="INICIAR_TORNEO", usuario_id=admin_id, fecha=datetime.now())
        self.match_repo.flush()
        self.match_repo.commit()
        self.match_repo.refresh(torneo)

        matches = self.match_repo.obtener_por_torneo(torneo_id)
        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=torneo.estado,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def _activar_ronda1_con_bracket(self, torneo_id: int) -> None:
        for bye in self.match_repo.obtener_byes_ronda1(torneo_id):
            bye.ganador_id = bye.jugador1_id
            bye.estado = _ESTADO_FINALIZADO
            self._avanzar_ganador_sencilla(torneo_id, bye)
        for m in self.match_repo.obtener_por_torneo_ronda(torneo_id, ronda=1):
            if m.jugador2_id is not None and m.estado != _ESTADO_FINALIZADO:
                m.estado = _ESTADO_EN_CURSO

    def registrar_resultado(
        self, torneo_id: int, match_id: int, ganador_id: int, admin_id: int
    ) -> ResultadoResponse:
        torneo = self._obtener_torneo_en_curso(torneo_id, admin_id)
        match = self._obtener_match_jugable(torneo_id, match_id)
        self._validar_ganador(match, ganador_id)

        perdedor_id = match.jugador2_id if ganador_id == match.jugador1_id else match.jugador1_id
        nuevo_elo_g, nuevo_elo_p = self._aplicar_elo(ganador_id, perdedor_id)

        match.ganador_id = ganador_id
        match.estado = _ESTADO_FINALIZADO

        torneo_finalizado = self._avanzar_segun_formato(torneo_id, torneo, match, ganador_id, perdedor_id)

        self.audit_repo.record(accion="REGISTRAR_RESULTADO", usuario_id=admin_id, fecha=datetime.now())
        if torneo_finalizado:
            torneo.estado = _ESTADO_FINALIZADO
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

    def _obtener_torneo_en_curso(self, torneo_id: int, admin_id: int):
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede registrar resultados",
            )
        if torneo.estado != _ESTADO_EN_CURSO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en curso",
            )
        return torneo

    def _obtener_match_jugable(self, torneo_id: int, match_id: int) -> MatchModel:
        match = self.match_repo.obtener_por_id(match_id)
        if match is None or match.torneo_id != torneo_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfrentamiento no encontrado en este torneo")
        if match.estado != _ESTADO_EN_CURSO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El enfrentamiento no está en curso",
            )
        return match

    @staticmethod
    def _validar_ganador(match: MatchModel, ganador_id: int) -> None:
        if ganador_id not in (match.jugador1_id, match.jugador2_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ganador debe ser uno de los participantes del enfrentamiento",
            )

    def _aplicar_elo(self, ganador_id: int, perdedor_id: int) -> tuple[int, int]:
        ganador_obj  = self.jugador_repo.obtener_por_id(ganador_id)
        perdedor_obj = self.jugador_repo.obtener_por_id(perdedor_id)
        nuevo_elo_g, nuevo_elo_p = self._calcular_nuevo_elo(ganador_obj.elo_global, perdedor_obj.elo_global)
        ganador_obj.elo_global  = nuevo_elo_g
        perdedor_obj.elo_global = nuevo_elo_p
        return nuevo_elo_g, nuevo_elo_p

    def _avanzar_segun_formato(
        self, torneo_id: int, torneo, match: MatchModel, ganador_id: int, perdedor_id: int
    ) -> bool:
        if torneo.tipo_eliminacion == _FORMATO_SENCILLA:
            return self._avanzar_ganador_sencilla(torneo_id, match) is None
        if torneo.tipo_eliminacion == _FORMATO_DOBLE:
            return self._procesar_resultado_doble(torneo_id, match, ganador_id, perdedor_id)
        if torneo.tipo_eliminacion in _FORMATOS_SWISS:
            return self._avanzar_swiss(torneo_id, torneo, match)
        self.match_repo.flush()
        return self.match_repo.contar_activos_por_torneo(torneo_id) == 0

    def _avanzar_swiss(self, torneo_id: int, torneo, match: MatchModel) -> bool:
        self.match_repo.flush()
        ronda_actual = match.ronda
        if self.match_repo.contar_activos_por_ronda(torneo_id, ronda_actual) != 0:
            return False
        ronda_siguiente = ronda_actual + 1
        if ronda_siguiente > torneo.rondas:
            return True
        nuevos = self._construir_swiss_siguiente_ronda(torneo_id, ronda_siguiente)
        self.match_repo.insertar_en_lote(nuevos)
        return False

    @staticmethod
    def _colocar_en_slot(match: MatchModel, slot: int, jugador_id: int) -> None:
        if slot == _SLOT_JUGADOR1:
            match.jugador1_id = jugador_id
        else:
            match.jugador2_id = jugador_id
        if match.jugador1_id is not None and match.jugador2_id is not None:
            match.estado = _ESTADO_EN_CURSO

    def _avanzar_ganador_sencilla(self, torneo_id: int, match: MatchModel) -> MatchModel | None:
        siguiente = self.match_repo.obtener_por_torneo_ronda_posicion(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=match.posicion // 2,
        )
        if siguiente is None:
            return None
        self._colocar_en_slot(siguiente, match.posicion % 2, match.ganador_id)
        return siguiente

    def _procesar_resultado_doble(
        self, torneo_id: int, match: MatchModel, ganador_id: int, perdedor_id: int
    ) -> bool:
        if match.bracket_tipo == _BRACKET_GANADORES:
            self._avanzar_ganador_doble(torneo_id, match, ganador_id)
            self._enviar_perdedor_a_perdedores(torneo_id, match, perdedor_id)
            return False
        if match.bracket_tipo == _BRACKET_PERDEDORES:
            self._avanzar_en_perdedores(torneo_id, match, ganador_id)
            return False
        if match.bracket_tipo == _BRACKET_GRAN_FINAL:
            return True
        return False

    def _avanzar_ganador_doble(self, torneo_id: int, match: MatchModel, ganador_id: int) -> None:
        siguiente = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=match.posicion // 2,
            bracket_tipo=_BRACKET_GANADORES,
        )
        if siguiente is not None:
            self._colocar_en_slot(siguiente, match.posicion % 2, ganador_id)
        else:
            self._colocar_en_gran_final(torneo_id, _SLOT_JUGADOR1, ganador_id)

    def _enviar_perdedor_a_perdedores(self, torneo_id: int, match: MatchModel, perdedor_id: int) -> None:
        lb_ronda, lb_pos, lb_slot = self._ruta_perdedor_a_perdedores(match.ronda, match.posicion)
        siguiente = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
            torneo_id=torneo_id, ronda=lb_ronda, posicion=lb_pos, bracket_tipo=_BRACKET_PERDEDORES,
        )
        if siguiente is not None:
            self._colocar_en_slot(siguiente, lb_slot, perdedor_id)

    def _avanzar_en_perdedores(self, torneo_id: int, match: MatchModel, ganador_id: int) -> None:
        if match.ronda % 2 == 1:
            next_pos, next_slot = match.posicion, _SLOT_JUGADOR1
        else:
            next_pos, next_slot = match.posicion // 2, match.posicion % 2

        siguiente = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=next_pos,
            bracket_tipo=_BRACKET_PERDEDORES,
        )
        if siguiente is not None:
            self._colocar_en_slot(siguiente, next_slot, ganador_id)
        else:
            self._colocar_en_gran_final(torneo_id, _SLOT_JUGADOR2, ganador_id)

    def _colocar_en_gran_final(self, torneo_id: int, slot: int, jugador_id: int) -> None:
        gran_final = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
            torneo_id=torneo_id, ronda=1, posicion=0, bracket_tipo=_BRACKET_GRAN_FINAL,
        )
        if gran_final is not None:
            self._colocar_en_slot(gran_final, slot, jugador_id)

    @staticmethod
    def _ruta_perdedor_a_perdedores(wb_ronda: int, wb_posicion: int) -> tuple[int, int, int]:
        if wb_ronda == 1:
            return 1, wb_posicion // 2, wb_posicion % 2
        lb_ronda = (wb_ronda - 1) * 2
        return lb_ronda, wb_posicion, 1

    @staticmethod
    def _factor_k(elo: int) -> int:
        if elo < _ELO_UMBRAL_NUEVO:
            return _ELO_K_NUEVO
        if elo < _ELO_UMBRAL_ELITE:
            return _ELO_K_ESTANDAR
        return _ELO_K_ELITE

    @staticmethod
    def _calcular_nuevo_elo(elo_ganador: int, elo_perdedor: int) -> tuple[int, int]:
        expected_winner = _PUNTOS_VICTORIA / (
            _PUNTOS_VICTORIA + _ELO_BASE ** ((elo_perdedor - elo_ganador) / _ELO_ESCALA)
        )
        k_winner = MatchService._factor_k(elo_ganador)
        k_loser  = MatchService._factor_k(elo_perdedor)
        nuevo_ganador  = round(elo_ganador + k_winner * (_PUNTOS_VICTORIA - expected_winner))
        nuevo_perdedor = round(elo_perdedor + k_loser * (_PUNTOS_DERROTA - expected_winner))
        return nuevo_ganador, nuevo_perdedor

    @staticmethod
    def _siguiente_potencia_de_dos(n: int) -> int:
        p = 1
        while p < n:
            p <<= 1
        return p

    def _sembrar_ronda1_ganadores(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        n = len(participantes)
        p = self._siguiente_potencia_de_dos(n)
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
                bracket_tipo=_BRACKET_GANADORES,
                jugador1_id=j1_id, jugador2_id=j2_id,
                ganador_id=None, estado=_ESTADO_PROGRAMADO,
            ))
        return matches

    def _rondas_ganadores_vacias(
        self, torneo_id: int, p: int, desde: int, hasta: int
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        for ronda in range(desde, hasta + 1):
            for pos in range(p // (2 ** ronda)):
                matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=ronda, posicion=pos,
                    bracket_tipo=_BRACKET_GANADORES,
                    jugador1_id=None, jugador2_id=None,
                    ganador_id=None, estado=_ESTADO_PENDIENTE,
                ))
        return matches

    def _construir_bracket_completo(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        p = self._siguiente_potencia_de_dos(len(participantes))
        total_rondas = p.bit_length() - 1
        return (
            self._sembrar_ronda1_ganadores(torneo_id, participantes)
            + self._rondas_ganadores_vacias(torneo_id, p, 2, total_rondas)
        )

    def _construir_eliminacion_doble(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        p = self._siguiente_potencia_de_dos(len(participantes))
        wb_rondas = p.bit_length() - 1
        lb_rondas = (wb_rondas - 1) * 2

        all_matches = self._sembrar_ronda1_ganadores(torneo_id, participantes)
        all_matches += self._rondas_ganadores_vacias(torneo_id, p, 2, wb_rondas)

        for ronda in range(1, lb_rondas + 1):
            k = (ronda + 1) // 2
            matches_en_ronda = p // (2 ** (k + 1))
            for pos in range(matches_en_ronda):
                all_matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=ronda, posicion=pos,
                    bracket_tipo=_BRACKET_PERDEDORES,
                    jugador1_id=None, jugador2_id=None,
                    ganador_id=None, estado=_ESTADO_PENDIENTE,
                ))

        all_matches.append(MatchModel(
            torneo_id=torneo_id, ronda=1, posicion=0,
            bracket_tipo=_BRACKET_GRAN_FINAL,
            jugador1_id=None, jugador2_id=None,
            ganador_id=None, estado=_ESTADO_PENDIENTE,
        ))

        return all_matches

    def _construir_round_robin(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        matches: list[MatchModel] = []
        n = len(participantes)
        pos = 0
        for i in range(n):
            for j in range(i + 1, n):
                matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=1, posicion=pos,
                    bracket_tipo=_BRACKET_GANADORES,
                    jugador1_id=participantes[i][0], jugador2_id=participantes[j][0],
                    ganador_id=None, estado=_ESTADO_PROGRAMADO,
                ))
                pos += 1
        return matches

    def _construir_swiss_ronda1(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        ordenados = sorted(participantes, key=lambda x: x[1], reverse=True)
        return self._emparejar_swiss(torneo_id, ronda=1, jugadores=[j[0] for j in ordenados], pares_jugados=set())

    def _construir_swiss_siguiente_ronda(self, torneo_id: int, ronda: int) -> list[MatchModel]:
        participantes = self.torneo_repo.obtener_participantes_confirmados(torneo_id)
        ids = {j[0] for j in participantes}

        victorias = self.match_repo.obtener_victorias_por_jugador(torneo_id)
        pares_jugados = self.match_repo.obtener_pares_jugados(torneo_id)

        jugadores_ordenados = sorted(ids, key=lambda jid: victorias.get(jid, 0), reverse=True)
        return self._emparejar_swiss(torneo_id, ronda, jugadores_ordenados, pares_jugados)

    @staticmethod
    def _emparejar_swiss(
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
                bracket_tipo=_BRACKET_GANADORES,
                jugador1_id=j1, jugador2_id=rival,
                ganador_id=None, estado=_ESTADO_EN_CURSO,
            ))
            pos += 1

        if disponibles:
            bye_jugador = disponibles[0]
            matches.append(MatchModel(
                torneo_id=torneo_id, ronda=ronda, posicion=pos,
                bracket_tipo=_BRACKET_GANADORES,
                jugador1_id=bye_jugador, jugador2_id=None,
                ganador_id=bye_jugador, estado=_ESTADO_FINALIZADO,
            ))

        return matches
