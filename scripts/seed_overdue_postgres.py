from datetime import date, timedelta

from app.core.database import SessionLocal
from app.domain.models.scheduled_match import ScheduledMatch


def _create_overdue_match(db) -> ScheduledMatch:
    yesterday = date.today() - timedelta(days=1)
    overdue_match = ScheduledMatch(
        match_status="Pendiente",
        score_detail="0-0",
        scheduled_datetime=yesterday,
    )
    db.add(overdue_match)
    db.commit()
    return overdue_match


def seed_overdue():
    db = SessionLocal()
    try:
        overdue_match = _create_overdue_match(db)
        print("Seeded scheduled_match id:", overdue_match.id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_overdue()
