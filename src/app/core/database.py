from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Register all ORM models in SQLAlchemy metadata at import-time.
# This prevents FK resolution issues in flows (scheduler/scripts)
# that touch only a subset of repositories/models.
from app.domain.models.alert import Alert  # noqa: F401,E402
from app.domain.models.elo_history import EloHistory  # noqa: F401,E402
from app.domain.models.player import Player  # noqa: F401,E402
from app.domain.models.scheduled_match import ScheduledMatch  # noqa: F401,E402
from app.models.audit_log import AuditLogModel  # noqa: F401,E402
from app.models.match import MatchModel  # noqa: F401,E402
from app.models.registration import RegistrationModel  # noqa: F401,E402
from app.models.tournament import TournamentModel  # noqa: F401,E402
