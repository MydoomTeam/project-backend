import os

# ruff: noqa: E402

_TEST_DATABASE_URL = "sqlite:///:memory:"
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.database as database

test_engine = create_engine(
    _TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    # SQLite no enforza FKs por defecto; las activamos para detectar
    # violaciones que de otro modo quedarían ocultas (ADR-006).
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


database.engine = test_engine
database.SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.domain.constants import SYSTEM_ADMIN_ID
from app.domain.models.alert import Alert  # noqa: F401
from app.domain.models.elo_history import EloHistory  # noqa: F401
from app.domain.models.player import Player  # noqa: F401
from app.domain.models.scheduled_match import ScheduledMatch  # noqa: F401
from app.models.audit_log import AuditLogModel  # noqa: F401
from app.models.match import MatchModel  # noqa: F401
from app.models.tournament import TournamentModel  # noqa: F401
from app.main import app
from app.repositories.player_repository import PlayerRepository

TestingSessionLocal = database.SessionLocal


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    # Actor de sistema (Player) para satisfacer audit_logs.user_id -> players.id,
    # equivalente a lo que hace el lifespan de la app en producción (ADR-005 5a).
    PlayerRepository(session).ensure_system_user(SYSTEM_ADMIN_ID)
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: 1

    with patch("app.main.start_scheduler", MagicMock()):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()
