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

_ELO_K = 32

_MIN_PARTICIPANTES_POR_TIPO: dict[str, int] = {
    "Eliminación Sencilla": 2,
    "Eliminación Doble": 4,
    "Round Robin": 3,
}


class MatchService:
    def __init__(self, db: Session):
        self.db = db
        self.torneo_repo = TournamentRepository(db)
        self.match_repo = MatchRepository(db)
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
        min_req = _MIN_PARTICIPANTES_POR_TIPO.get(torneo.tipo_eliminacion, 2)
        if len(participantes) < min_req:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Se requieren al menos {min_req} participantes confirmados para {torneo.tipo_eliminacion}",
            )

        if torneo.tipo_eliminacion != "Eliminación Sencilla":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El formato '{torneo.tipo_eliminacion}' no está implementado",
            )

        match_models = self._construir_bracket_completo(torneo_id, participantes)
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

        for bye_match in self.match_repo.obtener_byes_ronda1(torneo_id):
            bye_match.ganador_id = bye_match.jugador1_id
            bye_match.estado = "Finalizado"
            self._avanzar_ganador(torneo_id, bye_match)

        for m in self.match_repo.obtener_por_torneo_ronda(torneo_id, ronda=1):
            if m.jugador2_id is not None and m.estado != "Finalizado":
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

        ganador_obj = self.jugador_repo.obtener_por_id(ganador_id)
        perdedor_obj = self.jugador_repo.obtener_por_id(perdedor_id)
        nuevo_elo_g, nuevo_elo_p = self._calcular_nuevo_elo(ganador_obj.elo_global, perdedor_obj.elo_global)
        ganador_obj.elo_global = nuevo_elo_g
        perdedor_obj.elo_global = nuevo_elo_p

        match.ganador_id = ganador_id
        match.estado = "Finalizado"

        siguiente = self._avanzar_ganador(torneo_id, match)
        torneo_finalizado = siguiente is None

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

    def _avanzar_ganador(self, torneo_id: int, match: MatchModel) -> MatchModel | None:
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

    @staticmethod
    def _calcular_nuevo_elo(elo_ganador: int, elo_perdedor: int) -> tuple[int, int]:
        E_g = 1.0 / (1.0 + 10.0 ** ((elo_perdedor - elo_ganador) / 400.0))
        nuevo_g = round(elo_ganador + _ELO_K * (1.0 - E_g))
        nuevo_p = round(elo_perdedor + _ELO_K * (0.0 - (1.0 - E_g)))
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
        bye_count = p - n
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
                torneo_id=torneo_id,
                ronda=1,
                posicion=pos,
                jugador1_id=j1_id,
                jugador2_id=j2_id,
                ganador_id=None,
                estado="Programado",
            ))

        for ronda in range(2, total_rondas + 1):
            for pos in range(p // (2 ** ronda)):
                all_matches.append(MatchModel(
                    torneo_id=torneo_id,
                    ronda=ronda,
                    posicion=pos,
                    jugador1_id=None,
                    jugador2_id=None,
                    ganador_id=None,
                    estado="Pendiente",
                ))

        return all_matches
