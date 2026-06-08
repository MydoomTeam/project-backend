from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogModel
from app.models.match import MatchModel
from app.repositories.jugador_repository import JugadorRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.match import MatchResponse, ResultadoResponse
from app.schemas.tournament import BracketResponse

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

_FORMATOS_CON_BRACKET    = {"Eliminación Sencilla", "Eliminación Doble"}
_FORMATOS_TODOS_VS_TODOS = {"Round Robin"}
_FORMATOS_SWISS          = {"Swiss"}


class MatchService:
    def __init__(self, db: Session):
        self.db = db
        self.torneo_repo  = TournamentRepository(db)
        self.match_repo   = MatchRepository(db)
        self.jugador_repo = JugadorRepository(db)

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
        if torneo.estado != "Pendiente":
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

        if torneo.tipo_eliminacion == "Eliminación Sencilla":
            match_models = self._construir_bracket_completo(torneo_id, participantes)
        elif torneo.tipo_eliminacion == "Eliminación Doble":
            match_models = self._construir_eliminacion_doble(torneo_id, participantes)
        elif torneo.tipo_eliminacion in _FORMATOS_TODOS_VS_TODOS:
            match_models = self._construir_round_robin(torneo_id, participantes)
        elif torneo.tipo_eliminacion in _FORMATOS_SWISS:
            match_models = self._construir_swiss_ronda1(torneo_id, participantes)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El formato '{torneo.tipo_eliminacion}' no tiene generación de bracket implementada",
            )

        match_models = self.match_repo.insertar_en_lote(match_models)
        match_responses = [MatchResponse.model_validate(m) for m in match_models]

        torneo = self.torneo_repo.actualizar_estado_con_auditoria(
            torneo=torneo,
            nuevo_estado="Listo para iniciar",
            accion="GENERAR_BRACKET",
            fecha=datetime.now(),
            usuario_id=admin_id,
        )
        return BracketResponse(torneo_id=torneo_id, estado_torneo=torneo.estado, matches=match_responses)

    def iniciar_torneo(self, torneo_id: int, admin_id: int) -> BracketResponse:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede iniciar el torneo",
            )
        if torneo.estado != "Listo para iniciar":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en estado 'Listo para iniciar'",
            )

        if torneo.tipo_eliminacion in _FORMATOS_CON_BRACKET:
            for bye in self.match_repo.obtener_byes_ronda1(torneo_id):
                bye.ganador_id = bye.jugador1_id
                bye.estado = "Finalizado"
                self._avanzar_ganador_sencilla(torneo_id, bye)
            for m in self.match_repo.obtener_por_torneo_ronda(torneo_id, ronda=1):
                if m.jugador2_id is not None and m.estado != "Finalizado":
                    m.estado = "En curso"
        else:
            for m in self.match_repo.obtener_por_torneo(torneo_id):
                m.estado = "En curso"

        torneo.estado = "En curso"
        self.db.add(AuditLogModel(accion="INICIAR_TORNEO", fecha=datetime.now(), usuario_id=admin_id))
        self.db.flush()
        self.db.commit()
        self.db.refresh(torneo)

        matches = self.match_repo.obtener_por_torneo(torneo_id)
        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=torneo.estado,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def registrar_resultado(
        self, torneo_id: int, match_id: int, ganador_id: int, admin_id: int
    ) -> ResultadoResponse:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Torneo no encontrado")
        if torneo.creador_id != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador puede registrar resultados",
            )
        if torneo.estado != "En curso":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El torneo no está en curso",
            )

        match = self.match_repo.obtener_por_id(match_id)
        if match is None or match.torneo_id != torneo_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfrentamiento no encontrado en este torneo")
        if match.estado != "En curso":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El enfrentamiento no está en curso",
            )
        if ganador_id not in (match.jugador1_id, match.jugador2_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El ganador debe ser uno de los participantes del enfrentamiento",
            )

        perdedor_id = match.jugador2_id if ganador_id == match.jugador1_id else match.jugador1_id

        ganador_obj  = self.jugador_repo.obtener_por_id(ganador_id)
        perdedor_obj = self.jugador_repo.obtener_por_id(perdedor_id)
        nuevo_elo_g, nuevo_elo_p = self._calcular_nuevo_elo(ganador_obj.elo_global, perdedor_obj.elo_global)
        ganador_obj.elo_global  = nuevo_elo_g
        perdedor_obj.elo_global = nuevo_elo_p

        match.ganador_id = ganador_id
        match.estado = "Finalizado"

        torneo_finalizado = False

        if torneo.tipo_eliminacion == "Eliminación Sencilla":
            siguiente = self._avanzar_ganador_sencilla(torneo_id, match)
            torneo_finalizado = siguiente is None

        elif torneo.tipo_eliminacion == "Eliminación Doble":
            torneo_finalizado = self._procesar_resultado_doble(torneo_id, match, ganador_id, perdedor_id)

        elif torneo.tipo_eliminacion in _FORMATOS_SWISS:
            self.db.flush()
            ronda_actual = match.ronda
            if self.match_repo.contar_activos_por_ronda(torneo_id, ronda_actual) == 0:
                ronda_siguiente = ronda_actual + 1
                if ronda_siguiente <= torneo.rondas:
                    nuevos = self._construir_swiss_siguiente_ronda(torneo_id, ronda_siguiente)
                    self.match_repo.insertar_en_lote(nuevos)
                else:
                    torneo_finalizado = True
        else:
            self.db.flush()
            torneo_finalizado = self.match_repo.contar_activos_por_torneo(torneo_id) == 0

        self.db.add(AuditLogModel(accion="REGISTRAR_RESULTADO", fecha=datetime.now(), usuario_id=admin_id))
        if torneo_finalizado:
            torneo.estado = "Finalizado"
            self.db.add(AuditLogModel(accion="FINALIZAR_TORNEO", fecha=datetime.now(), usuario_id=admin_id))

        self.db.flush()
        self.db.commit()
        self.db.refresh(match)

        return ResultadoResponse(
            match=MatchResponse.model_validate(match),
            ganador_nuevo_elo=nuevo_elo_g,
            perdedor_nuevo_elo=nuevo_elo_p,
            torneo_finalizado=torneo_finalizado,
        )

    def _avanzar_ganador_sencilla(self, torneo_id: int, match: MatchModel) -> MatchModel | None:
        siguiente = self.match_repo.obtener_por_torneo_ronda_posicion(
            torneo_id=torneo_id,
            ronda=match.ronda + 1,
            posicion=match.posicion // 2,
        )
        if siguiente is None:
            return None
        if match.posicion % 2 == 0:
            siguiente.jugador1_id = match.ganador_id
        else:
            siguiente.jugador2_id = match.ganador_id
        if siguiente.jugador1_id is not None and siguiente.jugador2_id is not None:
            siguiente.estado = "En curso"
        return siguiente

    def _procesar_resultado_doble(
        self, torneo_id: int, match: MatchModel, ganador_id: int, perdedor_id: int
    ) -> bool:
        if match.bracket_tipo == _BRACKET_GANADORES:
            sig_g = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
                torneo_id=torneo_id,
                ronda=match.ronda + 1,
                posicion=match.posicion // 2,
                bracket_tipo=_BRACKET_GANADORES,
            )
            if sig_g is not None:
                if match.posicion % 2 == 0:
                    sig_g.jugador1_id = ganador_id
                else:
                    sig_g.jugador2_id = ganador_id
                if sig_g.jugador1_id is not None and sig_g.jugador2_id is not None:
                    sig_g.estado = "En curso"
            else:
                gran_final = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
                    torneo_id=torneo_id, ronda=1, posicion=0, bracket_tipo=_BRACKET_GRAN_FINAL,
                )
                if gran_final is not None:
                    gran_final.jugador1_id = ganador_id
                    if gran_final.jugador2_id is not None:
                        gran_final.estado = "En curso"

            lb_ronda, lb_pos, lb_slot = self._ruta_perdedor_a_perdedores(match.ronda, match.posicion)
            sig_lb = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
                torneo_id=torneo_id, ronda=lb_ronda, posicion=lb_pos, bracket_tipo=_BRACKET_PERDEDORES,
            )
            if sig_lb is not None:
                if lb_slot == 0:
                    sig_lb.jugador1_id = perdedor_id
                else:
                    sig_lb.jugador2_id = perdedor_id
                if sig_lb.jugador1_id is not None and sig_lb.jugador2_id is not None:
                    sig_lb.estado = "En curso"

        elif match.bracket_tipo == _BRACKET_PERDEDORES:
            sig_lb = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
                torneo_id=torneo_id,
                ronda=match.ronda + 1,
                posicion=match.posicion // 2,
                bracket_tipo=_BRACKET_PERDEDORES,
            )
            if sig_lb is not None:
                if match.posicion % 2 == 0:
                    sig_lb.jugador1_id = ganador_id
                else:
                    sig_lb.jugador2_id = ganador_id
                if sig_lb.jugador1_id is not None and sig_lb.jugador2_id is not None:
                    sig_lb.estado = "En curso"
            else:
                gran_final = self.match_repo.obtener_por_torneo_ronda_posicion_bracket(
                    torneo_id=torneo_id, ronda=1, posicion=0, bracket_tipo=_BRACKET_GRAN_FINAL,
                )
                if gran_final is not None:
                    gran_final.jugador2_id = ganador_id
                    if gran_final.jugador1_id is not None:
                        gran_final.estado = "En curso"

        elif match.bracket_tipo == _BRACKET_GRAN_FINAL:
            return True

        return False

    @staticmethod
    def _ruta_perdedor_a_perdedores(wb_ronda: int, wb_posicion: int) -> tuple[int, int, int]:
        lb_ronda = wb_ronda * 2 - 1
        lb_pos   = wb_posicion // 2
        lb_slot  = wb_posicion % 2
        return lb_ronda, lb_pos, lb_slot

    @staticmethod
    def _factor_k(elo: int) -> int:
        if elo < _ELO_UMBRAL_NUEVO:
            return _ELO_K_NUEVO
        if elo < _ELO_UMBRAL_ELITE:
            return _ELO_K_ESTANDAR
        return _ELO_K_ELITE

    @staticmethod
    def _calcular_nuevo_elo(elo_ganador: int, elo_perdedor: int) -> tuple[int, int]:
        E_g    = _PUNTOS_VICTORIA / (_PUNTOS_VICTORIA + _ELO_BASE ** ((elo_perdedor - elo_ganador) / _ELO_ESCALA))
        k_g    = MatchService._factor_k(elo_ganador)
        k_p    = MatchService._factor_k(elo_perdedor)
        nuevo_g = round(elo_ganador + k_g * (_PUNTOS_VICTORIA - E_g))
        nuevo_p = round(elo_perdedor + k_p * (_PUNTOS_DERROTA  - E_g))
        return nuevo_g, nuevo_p

    @staticmethod
    def _siguiente_potencia_de_dos(n: int) -> int:
        p = 1
        while p < n:
            p <<= 1
        return p

    def _construir_bracket_completo(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        n = len(participantes)
        p = self._siguiente_potencia_de_dos(n)
        bye_count   = p - n
        total_rondas = p.bit_length() - 1

        all_matches: list[MatchModel] = []

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
            all_matches.append(MatchModel(
                torneo_id=torneo_id, ronda=1, posicion=pos,
                bracket_tipo=_BRACKET_GANADORES,
                jugador1_id=j1_id, jugador2_id=j2_id,
                ganador_id=None, estado="Programado",
            ))

        for ronda in range(2, total_rondas + 1):
            for pos in range(p // (2 ** ronda)):
                all_matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=ronda, posicion=pos,
                    bracket_tipo=_BRACKET_GANADORES,
                    jugador1_id=None, jugador2_id=None,
                    ganador_id=None, estado="Pendiente",
                ))

        return all_matches

    def _construir_eliminacion_doble(
        self, torneo_id: int, participantes: list[tuple[int, int]]
    ) -> list[MatchModel]:
        n = len(participantes)
        p = self._siguiente_potencia_de_dos(n)
        bye_count    = p - n
        wb_rondas    = p.bit_length() - 1
        lb_rondas    = (wb_rondas - 1) * 2

        all_matches: list[MatchModel] = []

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
            all_matches.append(MatchModel(
                torneo_id=torneo_id, ronda=1, posicion=pos,
                bracket_tipo=_BRACKET_GANADORES,
                jugador1_id=j1_id, jugador2_id=j2_id,
                ganador_id=None, estado="Programado",
            ))

        for ronda in range(2, wb_rondas + 1):
            for pos in range(p // (2 ** ronda)):
                all_matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=ronda, posicion=pos,
                    bracket_tipo=_BRACKET_GANADORES,
                    jugador1_id=None, jugador2_id=None,
                    ganador_id=None, estado="Pendiente",
                ))

        for ronda in range(1, lb_rondas + 1):
            matches_en_ronda = max(1, p // (2 ** ((ronda + 2) // 2)))
            for pos in range(matches_en_ronda):
                all_matches.append(MatchModel(
                    torneo_id=torneo_id, ronda=ronda, posicion=pos,
                    bracket_tipo=_BRACKET_PERDEDORES,
                    jugador1_id=None, jugador2_id=None,
                    ganador_id=None, estado="Pendiente",
                ))

        all_matches.append(MatchModel(
            torneo_id=torneo_id, ronda=1, posicion=0,
            bracket_tipo=_BRACKET_GRAN_FINAL,
            jugador1_id=None, jugador2_id=None,
            ganador_id=None, estado="Pendiente",
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
                    ganador_id=None, estado="Programado",
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
                ganador_id=None, estado="En curso",
            ))
            pos += 1

        if disponibles:
            bye_jugador = disponibles[0]
            matches.append(MatchModel(
                torneo_id=torneo_id, ronda=ronda, posicion=pos,
                bracket_tipo=_BRACKET_GANADORES,
                jugador1_id=bye_jugador, jugador2_id=None,
                ganador_id=bye_jugador, estado="Finalizado",
            ))

        return matches
