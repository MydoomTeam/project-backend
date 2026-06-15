"""extend registration and match attributes phase 2

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-06-14 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("registrations", sa.Column("registration_date", sa.Date(), nullable=True))
    op.add_column("registrations", sa.Column("elo_seed", sa.Integer(), nullable=True))

    op.add_column("matches", sa.Column("next_match_id", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("score_detail", sa.Text(), nullable=True))
    op.add_column("matches", sa.Column("scheduled_datetime", sa.Date(), nullable=True))
    op.add_column("matches", sa.Column("result", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_matches_next_match_id",
        "matches",
        "matches",
        ["next_match_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_matches_next_match_id", "matches", type_="foreignkey")

    op.drop_column("matches", "result")
    op.drop_column("matches", "scheduled_datetime")
    op.drop_column("matches", "score_detail")
    op.drop_column("matches", "next_match_id")

    op.drop_column("registrations", "elo_seed")
    op.drop_column("registrations", "registration_date")
