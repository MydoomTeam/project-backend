"""rename registration columns to English (6C.3)

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-12 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Columnas de `registrations` a inglés (6C.3). El UniqueConstraint sigue
# automáticamente al rename de columnas en Postgres (constraint por OID).
_RENAMES = [
    ("torneo_id", "tournament_id"),
    ("jugador_id", "player_id"),
    ("estado", "status"),
]


def upgrade() -> None:
    for old, new in _RENAMES:
        op.alter_column("registrations", old, new_column_name=new)


def downgrade() -> None:
    for old, new in _RENAMES:
        op.alter_column("registrations", new, new_column_name=old)
