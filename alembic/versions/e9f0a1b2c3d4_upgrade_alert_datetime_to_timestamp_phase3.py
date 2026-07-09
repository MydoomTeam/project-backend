"""upgrade alert datetime to timestamp phase3

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-06-14 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import column, table

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename datetime -> created_at and upgrade Date -> DateTime on alerts
    op.add_column("alerts", sa.Column("created_at", sa.DateTime(), nullable=True))
    alerts_table = table(
        "alerts",
        column("datetime", sa.Date()),
        column("created_at", sa.DateTime()),
    )
    bind = op.get_bind()
    bind.execute(
        sa.update(alerts_table)
        .where(alerts_table.c.created_at.is_(None))
        .values(created_at=sa.cast(alerts_table.c.datetime, sa.DateTime()))
    )
    op.alter_column("alerts", "created_at", nullable=False)
    op.drop_column("alerts", "datetime")


def downgrade() -> None:
    op.add_column("alerts", sa.Column("datetime", sa.Date(), nullable=True))
    alerts_table = table(
        "alerts",
        column("datetime", sa.Date()),
        column("created_at", sa.DateTime()),
    )
    bind = op.get_bind()
    bind.execute(
        sa.update(alerts_table)
        .where(alerts_table.c.datetime.is_(None))
        .values(datetime=sa.cast(alerts_table.c.created_at, sa.Date()))
    )
    op.alter_column("alerts", "datetime", nullable=False)
    op.drop_column("alerts", "created_at")
