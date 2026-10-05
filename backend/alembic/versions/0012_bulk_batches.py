"""bulk upload: batches of items (each file or G.R. number is one main case)

Revision ID: 0012
Revises: 0011
"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bulk_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "bulk_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("bulk_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("gr_no", sa.String(32), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), server_default="queued", nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bulk_items_batch_status", "bulk_items", ["batch_id", "status"])
    op.create_index("ix_bulk_items_case_id", "bulk_items", ["case_id"])
    for table in ("bulk_batches", "bulk_items"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")  # Supabase exposes public tables: see 0009


def downgrade() -> None:
    op.drop_index("ix_bulk_items_case_id", table_name="bulk_items")
    op.drop_index("ix_bulk_items_batch_status", table_name="bulk_items")
    op.drop_table("bulk_items")
    op.drop_table("bulk_batches")
