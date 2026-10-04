"""case digests: the box a student fills for each cited case

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "digests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        # null = the stand-alone digest of a case (not inside any uploaded reviewer)
        sa.Column("upload_id", sa.Integer(), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=True),
        sa.Column("template", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("fields", postgresql.JSONB(), nullable=False),
        sa.Column("model", sa.String(64)),
        sa.Column("prompt_version", sa.String(32)),
        sa.Column("parser_version", sa.Integer()),
        sa.Column("ai_answered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # one digest per case per review (and one stand-alone digest per case): NULL upload_id counts as 0
    op.execute("CREATE UNIQUE INDEX uq_digests_case_upload ON digests (case_id, COALESCE(upload_id, 0))")
    op.create_index("ix_digests_upload_id", "digests", ["upload_id"])
    op.create_index("ix_digests_ai_answered_at", "digests", ["ai_answered_at"])


def downgrade() -> None:
    op.drop_table("digests")
