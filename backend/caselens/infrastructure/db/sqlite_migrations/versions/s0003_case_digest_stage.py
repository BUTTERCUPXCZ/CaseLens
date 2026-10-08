"""a digest being written says which step it is on (writing, checking, repairing) and since when, for the progress bar

Revision ID: s0003
Revises: s0002
"""
from alembic import op
import sqlalchemy as sa

revision = 's0003'
down_revision = 's0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('case_digests_v2', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stage', sa.String(16), nullable=True))
        batch_op.add_column(sa.Column('stage_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('case_digests_v2', schema=None) as batch_op:
        batch_op.drop_column('stage_at')
        batch_op.drop_column('stage')
