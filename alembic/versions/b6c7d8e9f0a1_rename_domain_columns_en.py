"""rename domain tables/columns to English (6C.6)

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-06-12 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Stack domain a inglés (6C.6). Tablas alerta->alerts, historialelo->elo_history.
# Valores (read_status "nueva", match_status "Pendiente", event_type "match_overdue")
# permanecen en español por ser contenido.
_ALERTS = [
    ("administrador_id", "admin_id"), ("jugador_id", "player_id"),
    ("tipo_evento", "event_type"), ("mensaje", "message"),
    ("fecha_hora", "datetime"), ("estado_lectura", "read_status"),
]
_ELO_HISTORY = [
    ("enfrentamiento_id", "match_id"), ("jugador_id", "player_id"),
    ("valor_elo_anterior", "previous_elo"), ("valor_elo_actual", "current_elo"),
    ("fecha_cambio", "change_date"),
]
_SCHEDULED = [
    ("match_siguiente_id", "next_match_id"), ("estado_match", "match_status"),
    ("marcador_detalle", "score_detail"), ("fecha_hora_programada", "scheduled_datetime"),
    ("resultado", "result"),
]


def upgrade() -> None:
    op.rename_table("alerta", "alerts")
    op.rename_table("historialelo", "elo_history")
    for old, new in _ALERTS:
        op.alter_column("alerts", old, new_column_name=new)
    for old, new in _ELO_HISTORY:
        op.alter_column("elo_history", old, new_column_name=new)
    for old, new in _SCHEDULED:
        op.alter_column("scheduled_matches", old, new_column_name=new)


def downgrade() -> None:
    for old, new in _SCHEDULED:
        op.alter_column("scheduled_matches", new, new_column_name=old)
    for old, new in _ELO_HISTORY:
        op.alter_column("elo_history", new, new_column_name=old)
    for old, new in _ALERTS:
        op.alter_column("alerts", new, new_column_name=old)
    op.rename_table("elo_history", "historialelo")
    op.rename_table("alerts", "alerta")
