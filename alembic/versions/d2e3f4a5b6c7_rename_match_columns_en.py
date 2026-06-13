"""rename match columns to English (6C.2)

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3d4e5f6
Create Date: 2026-06-12 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Columnas de `matches` a inglés (6C.2). Solo estructura; los VALORES
# (status "Pendiente", bracket_type "ganadores") permanecen en español.
_RENAMES = [
    ("torneo_id", "tournament_id"),
    ("ronda", "round"),
    ("posicion", "position"),
    ("bracket_tipo", "bracket_type"),
    ("jugador1_id", "player1_id"),
    ("jugador2_id", "player2_id"),
    ("ganador_id", "winner_id"),
    ("estado", "status"),
]


def upgrade() -> None:
    for old, new in _RENAMES:
        op.alter_column("matches", old, new_column_name=new)


def downgrade() -> None:
    for old, new in _RENAMES:
        op.alter_column("matches", new, new_column_name=old)
