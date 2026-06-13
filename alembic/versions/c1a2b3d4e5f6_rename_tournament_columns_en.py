"""rename tournament columns to English (6C.1)

Revision ID: c1a2b3d4e5f6
Revises: a256908dbd14
Create Date: 2026-06-12 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, None] = "a256908dbd14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Renombrado de columnas de la tabla `tournaments` a inglés (6C.1).
# Solo estructura; los VALORES (estado "Pendiente", tipo "Eliminación Sencilla")
# permanecen en español por ser contenido visible al usuario.
_RENAMES = [
    ("nombre", "name"),
    ("tipo_eliminacion", "elimination_type"),
    ("rondas", "rounds"),
    ("estado", "status"),
    ("creador_id", "creator_id"),
]


def upgrade() -> None:
    for old, new in _RENAMES:
        op.alter_column("tournaments", old, new_column_name=new)


def downgrade() -> None:
    for old, new in _RENAMES:
        op.alter_column("tournaments", new, new_column_name=old)
