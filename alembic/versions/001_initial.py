"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "request_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_id", sa.String(255), nullable=False),
        sa.Column("sport", sa.String(50), server_default="football"),
        sa.Column("market", sa.String(50), server_default="1x2"),
        sa.Column("is_ended", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_request_provider",
        "request_data",
        ["provider", "provider_id", "market"],
        unique=True,
    )

    op.create_table(
        "static_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_data_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("request_data.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("hash", sa.String(64), nullable=True),
        sa.Column("last_modified", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_static_path", "static_files", ["path"])
    op.create_index("idx_static_request", "static_files", ["request_data_id"])


def downgrade() -> None:
    op.drop_table("static_files")
    op.drop_table("request_data")
