"""a digest being written says which step it is on (writing, checking, repairing) and since when, for the progress bar

Revision ID: 0017
Revises: 0016
"""
import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("case_digests_v2", sa.Column("stage", sa.String(16), nullable=True))
    op.add_column("case_digests_v2", sa.Column("stage_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("case_digests_v2", "stage_at")
    op.drop_column("case_digests_v2", "stage")
