"""a bulk item can carry the exact Lawphil page the student picked (Individual): a decision and its Resolution share the number

Revision ID: s0002
Revises: s0001
"""
from alembic import op
import sqlalchemy as sa

revision = 's0002'
down_revision = 's0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('bulk_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_url', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('bulk_items', schema=None) as batch_op:
        batch_op.drop_column('source_url')
