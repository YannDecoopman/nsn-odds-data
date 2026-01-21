"""Add league_whitelists table

Revision ID: 003_add_league_whitelists
Revises: 002_add_api_keys
Create Date: 2026-01-20

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "003_add_league_whitelists"
down_revision: str | None = "002_add_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "league_whitelists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sport", sa.String(50), nullable=False, index=True),
        sa.Column("league_slug", sa.String(200), nullable=False, index=True),
        sa.Column("league_name", sa.String(300), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "uq_sport_league",
        "league_whitelists",
        ["sport", "league_slug"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_sport_league", table_name="league_whitelists")
    op.drop_table("league_whitelists")
