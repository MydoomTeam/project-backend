"""add uses_score to tournaments and score columns to matches

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-06-15 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("uses_score", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("matches", sa.Column("score_player1", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("score_player2", sa.Integer(), nullable=True))
    op.alter_column("tournaments", "uses_score", server_default=None)


def downgrade() -> None:
    op.drop_column("matches", "score_player2")
    op.drop_column("matches", "score_player1")
    op.drop_column("tournaments", "uses_score")
