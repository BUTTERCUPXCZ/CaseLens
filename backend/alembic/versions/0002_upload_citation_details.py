"""upload citation details: claimed date, reporter, unverified fields, message

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("upload_citations", sa.Column("claimed_date", sa.Date))
    op.add_column("upload_citations", sa.Column("reporter", sa.String(64)))
    op.add_column("upload_citations", sa.Column("unverified", postgresql.JSONB))
    op.add_column("upload_citations", sa.Column("message", sa.Text))


def downgrade() -> None:
    for column in ("message", "unverified", "reporter", "claimed_date"):
        op.drop_column("upload_citations", column)
