"""the case digest of a main case, in the client's format (one per case, written once)

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_digests_v2",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("state", sa.String(16), server_default="pending", nullable=False),
        sa.Column("sections", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("written", sa.Integer(), server_default="0", nullable=False),
        sa.Column("dropped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_case_digests_v2_created_at", "case_digests_v2", ["created_at"])
    op.execute("ALTER TABLE case_digests_v2 ENABLE ROW LEVEL SECURITY")  # Supabase exposes public tables: see 0009


def downgrade() -> None:
    op.drop_index("ix_case_digests_v2_created_at", table_name="case_digests_v2")
    op.drop_table("case_digests_v2")
