"""a student's own edits of a digest section, kept in their review; the reporter citation an uploaded file printed

- `review_digest_edits`: the text a student typed over one section of a case digest, in one review (upload). The shared AI digest is untouched.
- `bulk_items.reporter`: "177 SCRA 668" when the file printed it before the G.R. number (shown on the digest's citation line).

Revision ID: 0014
Revises: 0013
"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bulk_items", sa.Column("reporter", sa.String(64), nullable=True))
    op.create_table(
        "review_digest_edits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("bulk_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("digest_id", sa.Integer(), sa.ForeignKey("case_digests_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("batch_id", "digest_id", "section", name="uq_review_digest_edits_section"),
    )
    op.execute("ALTER TABLE review_digest_edits ENABLE ROW LEVEL SECURITY")  # Supabase exposes public tables: see 0009


def downgrade() -> None:
    op.drop_table("review_digest_edits")
    op.drop_column("bulk_items", "reporter")
