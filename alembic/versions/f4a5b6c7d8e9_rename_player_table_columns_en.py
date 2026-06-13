"""rename player table and columns to English (6C.4)

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-06-12 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tabla `jugador` -> `players` + columnas a inglés (6C.4). Las FK entrantes
# (audit_logs, matches, registrations, tournaments) siguen el rename de tabla
# automáticamente en Postgres (constraint por OID). Valores (role "JUGADOR")
# permanecen en español por ser contenido.
_COLUMNS = [
    ("nombre_usuario", "username"),
    ("correo_electronico", "email"),
    ("contrasena_hash", "password_hash"),
    ("rol", "role"),
    ("fecha_ultimo_acceso", "last_access_date"),
    ("elo_global", "global_elo"),
]


def upgrade() -> None:
    op.rename_table("jugador", "players")
    for old, new in _COLUMNS:
        op.alter_column("players", old, new_column_name=new)


def downgrade() -> None:
    for old, new in _COLUMNS:
        op.alter_column("players", new, new_column_name=old)
    op.rename_table("players", "jugador")
