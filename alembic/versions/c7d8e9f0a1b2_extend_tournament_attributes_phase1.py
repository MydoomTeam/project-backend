"""extend tournament attributes phase 1

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-06-14 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("game_name", sa.Text(), nullable=True))
    op.add_column("tournaments", sa.Column("game_category", sa.Text(), nullable=True))
    op.add_column("tournaments", sa.Column("participant_target", sa.Integer(), nullable=True))
    op.add_column("tournaments", sa.Column("round_duration_minutes", sa.Integer(), nullable=True))
    op.add_column("tournaments", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("tournaments", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("tournaments", sa.Column("language", sa.Text(), nullable=True))
    op.add_column("tournaments", sa.Column("region", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tournaments", "region")
    op.drop_column("tournaments", "language")
    op.drop_column("tournaments", "end_date")
    op.drop_column("tournaments", "start_date")
    op.drop_column("tournaments", "round_duration_minutes")
    op.drop_column("tournaments", "participant_target")
    op.drop_column("tournaments", "game_category")
    op.drop_column("tournaments", "game_name")
