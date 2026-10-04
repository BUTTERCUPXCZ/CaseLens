"""catalog of Lawphil's monthly lists: entries, their numbers, and which months were read

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("link_number", sa.String(32), nullable=False),
        sa.Column("label_key", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("decision_date", sa.Date),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column("index_url", sa.Text, nullable=False),
        sa.UniqueConstraint("source_url", "label_key", name="uq_catalog_entries_row"),
    )
    op.create_index("ix_catalog_entries_year_month", "catalog_entries", ["year", "month"])
    op.create_index(
        "ix_catalog_entries_title_trgm",
        "catalog_entries",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )

    op.create_table(
        "catalog_numbers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entry_id", sa.Integer, sa.ForeignKey("catalog_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.String(32), nullable=False),
    )
    op.create_index(
        "ix_catalog_numbers_number_prefix", "catalog_numbers", ["number"], postgresql_ops={"number": "text_pattern_ops"}
    )
    op.create_index("ix_catalog_numbers_entry_id", "catalog_numbers", ["entry_id"])

    op.create_table(
        "catalog_months",
        sa.Column("year", sa.Integer, primary_key=True),
        sa.Column("month", sa.Integer, primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("entries", sa.Integer, nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for table in ("catalog_months", "catalog_numbers", "catalog_entries"):
        op.drop_table(table)
