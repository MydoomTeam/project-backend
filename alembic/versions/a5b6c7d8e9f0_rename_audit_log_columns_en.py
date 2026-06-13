"""rename audit_log columns to English (6C.5)

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-06-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Columnas de `audit_logs` a inglés (6C.5). Los VALORES históricos
# (action "CREAR_TORNEO", etc.) permanecen en español (decisión previa).
_RENAMES = [
    ("accion", "action"),
    ("fecha", "created_at"),
    ("usuario_id", "user_id"),
    ("descripcion_cambio", "change_description"),
]


def upgrade() -> None:
    for old, new in _RENAMES:
        op.alter_column("audit_logs", old, new_column_name=new)


def downgrade() -> None:
    for old, new in _RENAMES:
        op.alter_column("audit_logs", new, new_column_name=old)
