"""sync postgres id sequences for databases initialized via arenasyncdbv2.sql

Revision ID: 002
Revises: 001
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "administrador",
    "jugador",
    "torneo",
    "ronda",
    "inscripcion",
    "enfrentamiento",
    "historialelo",
    "logauditoria",
    "alerta",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in TABLES:
        sequence = f"{table}_id_seq"
        op.execute(sa.text(f"CREATE SEQUENCE IF NOT EXISTS {sequence}"))
        op.execute(
            sa.text(
                f"SELECT setval('{sequence}', "
                f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
            )
        )
        op.execute(
            sa.text(f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT nextval('{sequence}')")
        )
        op.execute(sa.text(f"ALTER SEQUENCE {sequence} OWNED BY {table}.id"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in TABLES:
        sequence = f"{table}_id_seq"
        op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT"))
        op.execute(sa.text(f"DROP SEQUENCE IF EXISTS {sequence}"))
