"""the catalog lists decisions from two libraries: Lawphil and the Supreme Court E-Library (a decision Lawphil lacks is read there)

Revision ID: 0019
Revises: 0018
"""
import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catalog_entries", sa.Column("source", sa.String(16), server_default="lawphil", nullable=False))
    op.create_index("ix_catalog_entries_source_year_month", "catalog_entries", ["source", "year", "month"])
    # Search leaves out an E-Library row when Lawphil lists the same number and date: that check looks rows up by number.
    op.create_index("ix_catalog_entries_link_number_source", "catalog_entries", ["link_number", "source", "decision_date"])
    op.add_column("catalog_months", sa.Column("source", sa.String(16), server_default="lawphil", nullable=False))
    op.drop_constraint("catalog_months_pkey", "catalog_months", type_="primary")
    op.create_primary_key("catalog_months_pkey", "catalog_months", ["source", "year", "month"])


def downgrade() -> None:
    op.execute("DELETE FROM catalog_months WHERE source <> 'lawphil'")
    op.execute("DELETE FROM catalog_entries WHERE source <> 'lawphil'")
    op.drop_constraint("catalog_months_pkey", "catalog_months", type_="primary")
    op.create_primary_key("catalog_months_pkey", "catalog_months", ["year", "month"])
    op.drop_column("catalog_months", "source")
    op.drop_index("ix_catalog_entries_link_number_source", table_name="catalog_entries")
    op.drop_index("ix_catalog_entries_source_year_month", table_name="catalog_entries")
    op.drop_column("catalog_entries", "source")
