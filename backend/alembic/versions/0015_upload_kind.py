"""an upload is "individual" (one case: the student wants its full text) or "bulk" (many cases)

Revision ID: 0015
Revises: 0014
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bulk_batches", sa.Column("kind", sa.String(16), nullable=False, server_default="bulk"))


def downgrade() -> None:
    op.drop_column("bulk_batches", "kind")
