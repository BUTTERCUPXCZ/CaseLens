"""the student labels cases: several subject tags per case (the client's list), a topic scope per upload, a digest per case and scope,
and questions asked about a case

- `subjects` becomes the client's 11 tags (Civil Code -> Civil Law, Political and Administrative Law -> Political Law; Litigation and
  Administrative Law added; Philosophy of Law and Public International Law removed with their tags).
- `case_subjects`: a case can carry several tags; replaces `cases.subject_id` / `subject_source`.
- `bulk_batches`: the tags and the topic scope chosen once for the whole upload.
- `case_digests_v2`: one digest per case and scope (`scope_key` '' = the standard digest).
- `case_questions`: a question about a case and its checked answer.

Revision ID: 0013
Revises: 0012
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

TAGS = (
    "Civil Law", "Criminal Law", "Remedial Law", "Constitutional Law", "Labor Law", "Commercial Law",
    "Taxation Law", "Legal Ethics", "Political Law", "Litigation", "Administrative Law",
)
RENAMED = {"Civil Code": "Civil Law", "Political and Administrative Law": "Political Law"}
REMOVED = ("Philosophy of Law", "Public International Law")


def upgrade() -> None:
    # 1. the tags: rename, remove, add, then order them as the client's screen does
    for old, new in RENAMED.items():
        op.execute(sa.text("UPDATE subjects SET name = :new WHERE name = :old").bindparams(old=old, new=new))
    op.execute(sa.text("UPDATE cases SET subject_id = NULL, subject_source = NULL WHERE subject_id IN (SELECT id FROM subjects WHERE name = ANY(:names))").bindparams(names=list(REMOVED)))
    op.execute(sa.text("UPDATE bulk_batches SET subject_id = NULL WHERE subject_id IN (SELECT id FROM subjects WHERE name = ANY(:names))").bindparams(names=list(REMOVED)))
    op.execute(sa.text("DELETE FROM subjects WHERE name = ANY(:names)").bindparams(names=list(REMOVED)))
    for order, name in enumerate(TAGS, start=1):
        op.execute(
            sa.text(
                "INSERT INTO subjects (name, sort_order) VALUES (:name, :order) ON CONFLICT (name) DO UPDATE SET sort_order = EXCLUDED.sort_order"
            ).bindparams(name=name, order=order)
        )

    # 2. several tags per case
    op.create_table(
        "case_subjects",
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="student"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_case_subjects_subject_id", "case_subjects", ["subject_id"])
    op.execute(
        "INSERT INTO case_subjects (case_id, subject_id, source) "
        "SELECT id, subject_id, CASE WHEN subject_source = 'batch' THEN 'batch' ELSE 'student' END FROM cases WHERE subject_id IS NOT NULL"
    )
    op.drop_index("ix_cases_subject_id", table_name="cases")
    op.drop_column("cases", "subject_source")
    op.drop_column("cases", "subject_id")

    # 3. the upload's tags and topic scope
    op.add_column("bulk_batches", sa.Column("subject_ids", postgresql.ARRAY(sa.Integer()), nullable=False, server_default="{}"))
    op.add_column("bulk_batches", sa.Column("topic_scope", sa.String(300), nullable=False, server_default=""))
    op.execute("UPDATE bulk_batches SET subject_ids = ARRAY[subject_id] WHERE subject_id IS NOT NULL")
    op.drop_column("bulk_batches", "subject_id")

    # 4. a digest per case and scope
    op.add_column("case_digests_v2", sa.Column("scope", sa.String(300), nullable=False, server_default=""))
    op.add_column("case_digests_v2", sa.Column("scope_key", sa.String(300), nullable=False, server_default=""))
    op.drop_constraint("case_digests_v2_case_id_key", "case_digests_v2", type_="unique")
    op.create_unique_constraint("uq_case_digests_v2_case_scope", "case_digests_v2", ["case_id", "scope_key"])

    # 5. questions about a case
    op.create_table(
        "case_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("bulk_batches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", postgresql.JSONB(), nullable=True),
        sa.Column("state", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_case_questions_case_batch", "case_questions", ["case_id", "batch_id"])
    op.create_index("ix_case_questions_created_at", "case_questions", ["created_at"])
    for table in ("case_subjects", "case_questions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")  # Supabase exposes public tables: see 0009


def downgrade() -> None:
    op.drop_index("ix_case_questions_created_at", table_name="case_questions")
    op.drop_index("ix_case_questions_case_batch", table_name="case_questions")
    op.drop_table("case_questions")

    op.execute("DELETE FROM case_digests_v2 WHERE scope_key <> ''")  # only the standard digest fits the old one-per-case rule
    op.drop_constraint("uq_case_digests_v2_case_scope", "case_digests_v2", type_="unique")
    op.create_unique_constraint("case_digests_v2_case_id_key", "case_digests_v2", ["case_id"])
    op.drop_column("case_digests_v2", "scope_key")
    op.drop_column("case_digests_v2", "scope")

    op.add_column("bulk_batches", sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True))
    op.execute("UPDATE bulk_batches SET subject_id = subject_ids[1]")
    op.drop_column("bulk_batches", "topic_scope")
    op.drop_column("bulk_batches", "subject_ids")

    op.add_column("cases", sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True))
    op.add_column("cases", sa.Column("subject_source", sa.String(16), nullable=True))
    op.create_index("ix_cases_subject_id", "cases", ["subject_id"])
    op.execute(
        "UPDATE cases c SET subject_id = s.subject_id, subject_source = s.source "
        "FROM (SELECT DISTINCT ON (case_id) case_id, subject_id, source FROM case_subjects ORDER BY case_id, created_at) s WHERE s.case_id = c.id"
    )
    op.drop_index("ix_case_subjects_subject_id", table_name="case_subjects")
    op.drop_table("case_subjects")
    # the renamed and new tags stay: removing tags on the way down would lose students' labels
