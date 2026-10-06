"""a bulk item can carry the exact Lawphil page the student picked (Individual): a decision and its Resolution share the number

Revision ID: 0016
Revises: 0015
"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bulk_items", sa.Column("source_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bulk_items", "source_url")
