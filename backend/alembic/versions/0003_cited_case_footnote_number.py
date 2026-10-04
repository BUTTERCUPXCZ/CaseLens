"""cited cases remember which footnote cites them (deep link to #fntN)

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("case_citations", sa.Column("footnote_number", sa.Integer))


def downgrade() -> None:
    op.drop_column("case_citations", "footnote_number")
