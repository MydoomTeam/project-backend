import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData

from app.core.database import engine

# Esquema gestionado por Alembic (única fuente de verdad).
# Se elimina todo el esquema existente (incluida alembic_version) y se reconstruye
# aplicando el baseline canónico con `alembic upgrade head`.
_existing = MetaData()
_existing.reflect(bind=engine)
_existing.drop_all(bind=engine)

_repo_root = os.path.join(os.path.dirname(__file__), "..")
command.upgrade(Config(os.path.join(_repo_root, "alembic.ini")), "head")
print("Base de datos reiniciada vía Alembic (alembic upgrade head).")
