from datetime import date, timedelta

from app.domain.constants import SYSTEM_ADMIN_ID
from app.models.match import MatchModel
from app.models.tournament import TournamentModel


def seed_overdue_scheduled_match(session) -> MatchModel:
    past = date.today() - timedelta(days=1)

    tournament = TournamentModel(
        name="Torneo Seed Alertas",
        elimination_type="Eliminación Sencilla",
        rounds=1,
        status="Pendiente",
        creator_id=SYSTEM_ADMIN_ID,
    )
    session.add(tournament)
    session.flush()

    scheduled_match = MatchModel(
        tournament_id=tournament.id,
        round=1,
        position=1,
        bracket_type="ganadores",
        status="Programado",
        score_detail="0-0",
        scheduled_datetime=past,
    )
    session.add(scheduled_match)
    session.commit()
    return scheduled_match
