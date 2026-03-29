"""add aplus publish job payloads

Revision ID: 20260329_0005
Revises: 20260328_0004
Create Date: 2026-03-29 18:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_0005"
down_revision = "20260328_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "aplus_publish_jobs",
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("aplus_publish_jobs", "response_payload")
