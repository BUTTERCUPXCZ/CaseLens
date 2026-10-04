"""cases remember every G.R. number their page prints (joint decisions)

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("numbers", postgresql.ARRAY(sa.String(32)), server_default=sa.text("'{}'"), nullable=False),
    )
    # `manage reparse` fills this in for existing rows (the parser version is bumped).
    op.create_index("ix_cases_numbers", "cases", ["numbers"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_cases_numbers", table_name="cases")
    op.drop_column("cases", "numbers")
