from datetime import date, timedelta

from app.domain.models.scheduled_match import ScheduledMatch


def seed_overdue_scheduled_match(session) -> ScheduledMatch:
    past = date.today() - timedelta(days=1)
    scheduled_match = ScheduledMatch(
        id=1,
        match_status="Pendiente",
        score_detail="0-0",
        scheduled_datetime=past,
    )
    session.add(scheduled_match)
    session.commit()
    return scheduled_match
