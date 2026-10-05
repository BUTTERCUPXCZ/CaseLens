"""subjects, and one main case per case (no redundancy)

Revision ID: 0010
Revises: 0009

- `subjects`: the library's filter (Civil Code, Constitutional Law, ...), seeded.
- `cases.subject_id` / `subject_source`: which subject a case is filed under, and who chose it.
- `cases.main_case_id`: a page that only belongs to another case (a Resolution, the same decision under another G.R. number)
  points at its main case; the library lists main cases only. Backfilled: the oldest stored page of a family is its main case.
- (The GIN index on `cases.numbers` already exists from 0005; it keeps "which stored pages print this G.R. number" fast.)
- Row Level Security on the new table (Supabase exposes public tables; see 0009).
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

SUBJECTS = (
    "Civil Code", "Constitutional Law", "Remedial Law", "Philosophy of Law", "Criminal Law", "Labor Law",
    "Taxation Law", "Commercial Law", "Political and Administrative Law", "Legal Ethics", "Public International Law",
)


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )
    op.execute("ALTER TABLE subjects ENABLE ROW LEVEL SECURITY")
    subjects = sa.table("subjects", sa.column("name", sa.String), sa.column("sort_order", sa.Integer))
    op.bulk_insert(subjects, [{"name": name, "sort_order": order} for order, name in enumerate(SUBJECTS, start=1)])

    op.add_column("cases", sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True))
    op.add_column("cases", sa.Column("subject_source", sa.String(16), nullable=True))
    op.add_column("cases", sa.Column("main_case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_cases_subject_id", "cases", ["subject_id"])
    op.create_index("ix_cases_main_case_id", "cases", ["main_case_id"])

    # Backfill: pages that print a G.R. number another (older) stored page prints belong to that page's family.
    op.execute(
        """
        UPDATE cases c SET main_case_id = m.id
        FROM (
            SELECT c2.id AS case_id, MIN(o.id) AS id
            FROM cases c2
            JOIN cases o ON o.id < c2.id AND (o.numbers && c2.numbers OR o.gr_no = c2.gr_no OR o.gr_no = ANY (c2.numbers) OR c2.gr_no = ANY (o.numbers))
            GROUP BY c2.id
        ) m
        WHERE c.id = m.case_id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_cases_main_case_id", table_name="cases")
    op.drop_index("ix_cases_subject_id", table_name="cases")
    op.drop_column("cases", "main_case_id")
    op.drop_column("cases", "subject_source")
    op.drop_column("cases", "subject_id")
    op.drop_table("subjects")
