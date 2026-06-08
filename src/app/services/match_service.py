from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.match import MatchModel
from app.repositories.match_repository import MatchRepository
from app.repositories.tournament_repository import TournamentRepository
from app.schemas.match import MatchResponse
from app.schemas.tournament import BracketResponse

_MIN_PARTICIPANTES = 2

class MatchService:
    def __init__(self, db: Session):
        self.torneo_repo = TournamentRepository(db)
        self.match_repo = MatchRepository(db)

    def obtener_bracket(self, torneo_id: int) -> BracketResponse:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )
        matches = self.match_repo.obtener_por_torneo(torneo_id)
        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=torneo.estado,
            matches=[MatchResponse.model_validate(m) for m in matches],
        )

    def generar_bracket(self, torneo_id: int, admin_id: int) -> BracketResponse:
        torneo = self.torneo_repo.obtener_por_id(torneo_id)
        if torneo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Torneo no encontrado",
            )

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
        if len(participantes) < _MIN_PARTICIPANTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Se requieren al menos {_MIN_PARTICIPANTES} participantes confirmados para generar el cuadro",
            )

        match_models = self._construir_ronda1(torneo_id, participantes)
        match_models = self.match_repo.insertar_en_lote(match_models)

        match_responses = [MatchResponse.model_validate(m) for m in match_models]

        torneo = self.torneo_repo.actualizar_estado_con_auditoria(
            torneo=torneo,
            nuevo_estado="Listo para iniciar",
            accion="GENERAR_BRACKET",
            fecha=datetime.now(),
            usuario_id=admin_id,
        )

        return BracketResponse(
            torneo_id=torneo_id,
            estado_torneo=torneo.estado,
            matches=match_responses,
        )

    @staticmethod
    def _siguiente_potencia_de_dos(n: int) -> int:
        p = 1
        while p < n:
            p <<= 1
        return p

    def _construir_ronda1(
        self,
        torneo_id: int,
        participantes: list[tuple[int, int]],
    ) -> list[MatchModel]:
        n = len(participantes)
        p = self._siguiente_potencia_de_dos(n)
        bye_count = p - n

        matches: list[MatchModel] = []

        for i in range(bye_count):
            matches.append(
                MatchModel(
                    torneo_id=torneo_id,
                    ronda=1,
                    jugador1_id=participantes[i][0],
                    jugador2_id=None,
                    estado="Programado",
                )
            )

        restantes = participantes[bye_count:]
        for i in range(0, len(restantes), 2):
            matches.append(
                MatchModel(
                    torneo_id=torneo_id,
                    ronda=1,
                    jugador1_id=restantes[i][0],
                    jugador2_id=restantes[i + 1][0],
                    estado="Programado",
                )
            )

        return matches
