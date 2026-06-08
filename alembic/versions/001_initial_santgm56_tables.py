"""initial schema aligned with arenasyncdbv2.sql

Revision ID: 001
Revises:
Create Date: 2026-06-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "administrador",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("nombre_usuario", sa.Text(), nullable=False),
        sa.Column("correo_electronico", sa.Text(), nullable=False),
        sa.Column("contrasena_hash", sa.Text(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("fecha_ultimo_acceso", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "jugador",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("nombre_usuario", sa.Text(), nullable=False),
        sa.Column("correo_electronico", sa.Text(), nullable=False),
        sa.Column("contrasena_hash", sa.Text(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("fecha_ultimo_acceso", sa.Date(), nullable=False),
        sa.Column("elo_global", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "torneo",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("administrador_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("tipo_eliminacion", sa.Text(), nullable=False),
        sa.Column("nombre_juego", sa.Text(), nullable=False),
        sa.Column("categoria_juego", sa.Text(), nullable=False),
        sa.Column("numero_participantes", sa.Integer(), nullable=False),
        sa.Column("numero_rondas", sa.Integer(), nullable=False),
        sa.Column("duracion_ronda", sa.Integer(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("idioma", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["administrador_id"], ["administrador.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ronda",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("torneo_id", sa.Integer(), nullable=False),
        sa.Column("numero_fase", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["torneo_id"], ["torneo.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "inscripcion",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("torneo_id", sa.Integer(), nullable=False),
        sa.Column("jugador_id", sa.Integer(), nullable=False),
        sa.Column("estado_participante", sa.Text(), nullable=False),
        sa.Column("fecha_inscripcion", sa.Date(), nullable=False),
        sa.Column("elo_seed", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["jugador_id"], ["jugador.id"]),
        sa.ForeignKeyConstraint(["torneo_id"], ["torneo.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "enfrentamiento",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("ronda_id", sa.Integer(), nullable=False),
        sa.Column("inscripcion_a_id", sa.Integer(), nullable=False),
        sa.Column("inscripcion_b_id", sa.Integer(), nullable=False),
        sa.Column("match_siguiente_id", sa.Integer(), nullable=True),
        sa.Column("estado_match", sa.Text(), nullable=False),
        sa.Column("marcador_detalle", sa.Text(), nullable=False),
        sa.Column("fecha_hora_programada", sa.Date(), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["inscripcion_a_id"], ["inscripcion.id"]),
        sa.ForeignKeyConstraint(["inscripcion_b_id"], ["inscripcion.id"]),
        sa.ForeignKeyConstraint(["match_siguiente_id"], ["enfrentamiento.id"]),
        sa.ForeignKeyConstraint(["ronda_id"], ["ronda.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "historialelo",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("enfrentamiento_id", sa.Integer(), nullable=False),
        sa.Column("jugador_id", sa.Integer(), nullable=False),
        sa.Column("valor_elo_anterior", sa.Integer(), nullable=False),
        sa.Column("valor_elo_actual", sa.Integer(), nullable=False),
        sa.Column("fecha_cambio", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["enfrentamiento_id"], ["enfrentamiento.id"]),
        sa.ForeignKeyConstraint(["jugador_id"], ["jugador.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "logauditoria",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("administrador_id", sa.Integer(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("TIMESTAMP", sa.Date(), nullable=False),
        sa.Column("descripcion_cambio", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["administrador_id"], ["administrador.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "alerta",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("administrador_id", sa.Integer(), nullable=True),
        sa.Column("jugador_id", sa.Integer(), nullable=True),
        sa.Column("tipo_evento", sa.Text(), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("fecha_hora", sa.Date(), nullable=False),
        sa.Column("estado_lectura", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["administrador_id"], ["administrador.id"]),
        sa.ForeignKeyConstraint(["jugador_id"], ["jugador.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("alerta")
    op.drop_table("logauditoria")
    op.drop_table("historialelo")
    op.drop_table("enfrentamiento")
    op.drop_table("inscripcion")
    op.drop_table("ronda")
    op.drop_table("torneo")
    op.drop_table("jugador")
    op.drop_table("administrador")
