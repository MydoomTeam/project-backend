import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData

from app.core.database import engine


def _resolve_environment() -> str:
	return (
		os.getenv("APP_ENV")
		or os.getenv("ENVIRONMENT")
		or os.getenv("FASTAPI_ENV")
		or os.getenv("PYTHON_ENV")
		or "development"
	).strip().lower()


def _assert_safe_to_reset() -> None:
	environment = _resolve_environment()
	if environment in {"prod", "production"}:
		raise RuntimeError("Reset abortado: no está permitido en entorno de producción.")

	confirmation = os.getenv("RESET_DB_CONFIRM", "").strip().upper()
	if confirmation != "YES":
		raise RuntimeError(
			"Reset abortado: define RESET_DB_CONFIRM=YES para confirmar el borrado total del esquema."
		)


def main() -> None:
	_assert_safe_to_reset()

	# Esquema gestionado por Alembic (única fuente de verdad).
	# Se elimina todo el esquema existente (incluida alembic_version) y se reconstruye
	# aplicando el baseline canónico con alembic upgrade head.
	existing_schema = MetaData()
	existing_schema.reflect(bind=engine)
	existing_schema.drop_all(bind=engine)

	repo_root = os.path.join(os.path.dirname(__file__), "..")
	command.upgrade(Config(os.path.join(repo_root, "alembic.ini")), "head")
	print("Base de datos reiniciada vía Alembic (alembic upgrade head).")


if __name__ == "__main__":
	main()
