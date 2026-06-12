"""drop_administrador_table

Revision ID: a256908dbd14
Revises: 8dd23c0649ac
Create Date: 2026-06-12 17:19:38.328755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a256908dbd14'
down_revision: Union[str, None] = '8dd23c0649ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Elimina la tabla legada `administrador` (stack de identidad dual ya desmontado en 5d.1).
    # Sin FKs entrantes/salientes -> drop directo. No toca ninguna otra tabla.
    op.drop_table("administrador")


def downgrade() -> None:
    # Recrea `administrador` con la estructura EXACTA del baseline (8dd23c0649ac).
    op.create_table(
        "administrador",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("nombre_usuario", sa.Text(), nullable=False),
        sa.Column("correo_electronico", sa.Text(), nullable=False),
        sa.Column("contrasena_hash", sa.Text(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("fecha_ultimo_acceso", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
