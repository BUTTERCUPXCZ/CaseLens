"""initial schema

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("gr_no", sa.String(32), nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("decision_date", sa.Date),
        sa.Column("doc_type", sa.String(32), server_default="decision", nullable=False),
        sa.Column("ponente", sa.String(128)),
        sa.Column("division", sa.String(64)),
        sa.Column("disposition", sa.String(32)),
        sa.Column("source_url", sa.Text, nullable=False, unique=True),
        sa.Column("raw_html", sa.Text, nullable=False),
        sa.Column("full_text", sa.Text, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("parser_version", sa.Integer, nullable=False),
    )
    op.create_index("ix_cases_gr_no", "cases", ["gr_no"])
    op.create_index(
        "ix_cases_title_trgm",
        "cases",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_cases_full_text_fts",
        "cases",
        [sa.text("to_tsvector('english', full_text)")],
        postgresql_using="gin",
    )

    op.create_table(
        "case_opinions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("author", sa.String(128)),
        sa.Column("text", sa.Text, nullable=False),
    )
    op.create_index("ix_case_opinions_case_id", "case_opinions", ["case_id"])

    op.create_table(
        "case_footnotes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opinion_id", sa.Integer, sa.ForeignKey("case_opinions.id", ondelete="CASCADE")),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("anchor", sa.String(32), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
    )
    op.create_index("ix_case_footnotes_case_id", "case_footnotes", ["case_id"])

    op.create_table(
        "case_statutes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("statute_type", sa.String(16), nullable=False),
        sa.Column("number", sa.String(32), nullable=False),
        sa.Column("raw", sa.Text, nullable=False),
    )
    op.create_index("ix_case_statutes_case_id", "case_statutes", ["case_id"])
    op.create_index("ix_case_statutes_type_number", "case_statutes", ["statute_type", "number"])

    op.create_table(
        "case_citations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cited_title", sa.Text, nullable=False),
        sa.Column("cited_gr_no", sa.String(32)),
        sa.Column("source", sa.String(16), nullable=False),
    )
    op.create_index("ix_case_citations_case_id", "case_citations", ["case_id"])
    op.create_index("ix_case_citations_cited_gr_no", "case_citations", ["cited_gr_no"])

    op.create_table(
        "month_indexes",
        sa.Column("url", sa.Text, primary_key=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("links", postgresql.JSONB, nullable=False),
    )

    op.create_table(
        "uploads",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "upload_citations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("upload_id", sa.Integer, sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_citation", sa.Text, nullable=False),
        sa.Column("gr_no", sa.String(32), nullable=False),
        sa.Column("claimed_year", sa.Integer),
        sa.Column("claimed_title", sa.Text),
        sa.Column("matched_case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("mismatches", postgresql.JSONB),
    )
    op.create_index("ix_upload_citations_upload_id", "upload_citations", ["upload_id"])
    op.create_index("ix_upload_citations_gr_no", "upload_citations", ["gr_no"])


def downgrade() -> None:
    for table in (
        "upload_citations",
        "uploads",
        "month_indexes",
        "case_citations",
        "case_statutes",
        "case_footnotes",
        "case_opinions",
        "cases",
    ):
        op.drop_table(table)
