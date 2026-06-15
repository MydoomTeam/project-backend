"""upgrade alert datetime to timestamp phase3

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-06-14 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename datetime -> created_at and upgrade Date -> DateTime on alerts
    op.add_column("alerts", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE alerts SET created_at = datetime::timestamp WHERE created_at IS NULL")
    op.alter_column("alerts", "created_at", nullable=False)
    op.drop_column("alerts", "datetime")


def downgrade() -> None:
    op.add_column("alerts", sa.Column("datetime", sa.Date(), nullable=True))
    op.execute("UPDATE alerts SET datetime = created_at::date WHERE datetime IS NULL")
    op.alter_column("alerts", "datetime", nullable=False)
    op.drop_column("alerts", "created_at")
