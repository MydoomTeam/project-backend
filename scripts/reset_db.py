import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import MetaData
from app.core.database import Base, engine
from app.models import audit_log, match, registration, tournament  # noqa: F401
from app.domain.models import jugador  # noqa: F401

todas_las_tablas = MetaData()
todas_las_tablas.reflect(bind=engine)
todas_las_tablas.drop_all(bind=engine)

Base.metadata.create_all(bind=engine)
print("Base de datos reiniciada correctamente.")
