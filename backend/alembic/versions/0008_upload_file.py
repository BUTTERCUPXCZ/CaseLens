"""uploads keep the original file, so the finished reviewer can be built from it

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("uploads", sa.Column("file_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("uploads", "file_data")
