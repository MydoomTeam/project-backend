import os

_TEST_DATABASE_URL = "sqlite:///:memory:"
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock, patch

import app.core.database as database

test_engine = create_engine(
    _TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
database.engine = test_engine
database.SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)

from app.core.database import Base, get_db
from app.controllers.admin_controller import get_current_admin_id
from app.core.auth import get_current_user
from app.domain.models.admin import Administrador  # noqa: F401
from app.domain.models.alerta import Alerta  # noqa: F401
from app.domain.models.scheduled_match import ScheduledMatch  # noqa: F401
from app.domain.models.historialelo import HistorialElo  # noqa: F401
from app.domain.models.jugador import Jugador  # noqa: F401
from app.main import app
from tests.helpers import seed_admin

TestingSessionLocal = database.SessionLocal


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    seed_admin(session)
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
    app.dependency_overrides[get_current_admin_id] = lambda: 1
    app.dependency_overrides[get_current_user] = lambda: 1

    with patch("app.main.start_scheduler", MagicMock()):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()
