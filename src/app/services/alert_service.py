import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.schemas.alert import AlertActivityResponse, AlertResponse
from app.models.match import MatchModel
from app.models.registration import RegistrationModel
from app.models.tournament import TournamentModel
from app.repositories.alert_repository import AlertRepository
from app.repositories.audit_log_repository import AuditLogRepository

_TOURNAMENT_ID_EQ_PATTERN = re.compile(r"tournament_id=(\d+)")
_TOURNAMENT_ID_COLON_PATTERN = re.compile(r"Tournament:(\d+)")
_MATCH_ID_PATTERN = re.compile(r"match_id=(\d+)")
_PLAYER_STATUS_PATTERN = re.compile(r"Player:(\d+):([^:]+)$")

_ACTION_LABELS: dict[str, str] = {
    "CREAR_TORNEO": "Creacion de torneo",
    "CANCELAR_TORNEO": "Cancelacion de torneo",
    "GENERAR_BRACKET": "Bracket generado",
    "INICIAR_TORNEO": "Torneo iniciado",
    "REGISTRAR_RESULTADO": "Resultado registrado",
    "FINALIZAR_TORNEO": "Torneo finalizado",
    "UPDATE_REGISTRATION_STATUS": "Inscripcion actualizada",
    "ACK_ALERTA": "Alerta reconocida",
}


class AlertService:
    def __init__(self, alert_repo: AlertRepository, audit_repo: AuditLogRepository, db: Session | None = None):
        self.alert_repo = alert_repo
        self.audit_repo = audit_repo
        self.db = db

    @classmethod
    def from_session(cls, db: Session) -> "AlertService":
        return cls(AlertRepository(db), AuditLogRepository(db), db)

    def get_alerts(self, viewer_id: int | None = None) -> dict:
        alerts = [self._to_response(alert) for alert in self.alert_repo.get_all()]
        if viewer_id is None:
            recent_logs = self.audit_repo.list_recent(limit=12)
            if recent_logs is None:
                recent_logs = []
            else:
                try:
                    iter(recent_logs)
                except TypeError:
                    recent_logs = []

            history = [
                AlertActivityResponse(
                    id=log.id,
                    action=log.action,
                    action_label=_ACTION_LABELS.get(log.action),
                    created_at=log.created_at,
                    description=log.change_description,
                )
                for log in recent_logs
                if log.action != "CHECK_OVERDUE_OK"
            ]
        else:
            history = self._build_visible_history(viewer_id)
        return {
            "items": alerts,
            "stats": {
                "total": len(alerts),
                "new": sum(1 for alert in alerts if alert.status == "nueva"),
                "acknowledged": sum(1 for alert in alerts if alert.status == "reconocida"),
                "critical": sum(1 for alert in alerts if alert.event_type == "match_overdue" and alert.status == "nueva"),
            },
            "history": history,
        }

    def acknowledge_alert(self, actor_id: int, alert_id: int):
        alert = self.alert_repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alerta no encontrada")

        self.alert_repo.acknowledge(alert)
        self.audit_repo.log_action(
            actor_id=actor_id,
            action="ACK_ALERTA",
            change_description=f"Alert:{alert_id}",
        )
        return {"message": "acknowledged"}

    @staticmethod
    def _to_response(alert) -> AlertResponse:
        return AlertResponse(
            id=alert.id,
            event_type=alert.event_type,
            message=alert.message,
            created_at=alert.created_at,
            status=alert.read_status,
        )

    def _build_visible_history(self, viewer_id: int) -> list[AlertActivityResponse]:
        if self.db is None:
            return []

        visible_tournament_ids = self._get_user_related_tournament_ids(viewer_id)
        if not visible_tournament_ids:
            return []

        tournament_names = dict(
            self.db.execute(
                select(TournamentModel.id, TournamentModel.name).where(
                    TournamentModel.id.in_(visible_tournament_ids),
                )
            ).all()
        )

        history: list[AlertActivityResponse] = []
        for log in self.audit_repo.list_recent(limit=80):
            if log.action in {"CHECK_OVERDUE_OK", "CREATE_ALERTA", "CREATE_ALERTA_FAILED"}:
                continue
            entry = self._to_activity(log, visible_tournament_ids, tournament_names)
            if entry is not None:
                history.append(entry)
            if len(history) >= 12:
                break
        return history

    def _get_user_related_tournament_ids(self, viewer_id: int) -> set[int]:
        if self.db is None:
            return set()

        created_ids = {
            row[0]
            for row in self.db.execute(
                select(TournamentModel.id).where(TournamentModel.creator_id == viewer_id)
            ).all()
        }

        registered_ids = {
            row[0]
            for row in self.db.execute(
                select(RegistrationModel.tournament_id).where(RegistrationModel.player_id == viewer_id)
            ).all()
        }

        return created_ids | registered_ids

    def _extract_tournament_id(self, log) -> int | None:
        description = (log.change_description or "").strip()

        match = _TOURNAMENT_ID_EQ_PATTERN.search(description)
        if match:
            return int(match.group(1))

        match = _TOURNAMENT_ID_COLON_PATTERN.search(description)
        if match:
            return int(match.group(1))

        match = _MATCH_ID_PATTERN.search(description)
        if match and self.db is not None:
            match_id = int(match.group(1))
            match_row = self.db.execute(
                select(MatchModel.tournament_id).where(MatchModel.id == match_id)
            ).first()
            if match_row:
                return int(match_row[0])

        return None

    def _to_activity(
        self,
        log,
        visible_tournament_ids: set[int],
        tournament_names: dict[int, str],
    ) -> AlertActivityResponse | None:
        tournament_id = self._extract_tournament_id(log)
        if tournament_id is None or tournament_id not in visible_tournament_ids:
            return None

        tournament_name = tournament_names.get(tournament_id)
        action_label = _ACTION_LABELS.get(log.action, "Actividad del torneo")

        description = self._to_natural_description(log.action, log.change_description, tournament_name)
        return AlertActivityResponse(
            id=log.id,
            action=log.action,
            action_label=action_label,
            created_at=log.created_at,
            description=description,
            tournament_id=tournament_id,
            tournament_name=tournament_name,
        )

    @staticmethod
    def _to_natural_description(action: str, change_description: str | None, tournament_name: str | None) -> str:
        tournament_label = tournament_name or "torneo"

        if action == "CREAR_TORNEO":
            return f"Se creo el torneo {tournament_label}."
        if action == "CANCELAR_TORNEO":
            return f"Se cancelo el torneo {tournament_label}."
        if action == "GENERAR_BRACKET":
            return f"Se genero el bracket del torneo {tournament_label}."
        if action == "INICIAR_TORNEO":
            return f"El torneo {tournament_label} inicio."
        if action == "FINALIZAR_TORNEO":
            return f"El torneo {tournament_label} finalizo."
        if action == "REGISTRAR_RESULTADO":
            return f"Se registro un resultado de partida en {tournament_label}."
        if action == "UPDATE_REGISTRATION_STATUS":
            detail = (change_description or "").strip()
            status_match = _PLAYER_STATUS_PATTERN.search(detail)
            if status_match:
                player_id = status_match.group(1)
                status_value = status_match.group(2)
                return f"La inscripcion del jugador #{player_id} en {tournament_label} cambio a {status_value}."
            return f"Se actualizo un estado de inscripcion en {tournament_label}."

        return f"Se registro una actividad en {tournament_label}."
