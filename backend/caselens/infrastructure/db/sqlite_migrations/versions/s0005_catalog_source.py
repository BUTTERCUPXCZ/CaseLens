"""the catalog lists decisions from two libraries: Lawphil and the Supreme Court E-Library (a decision Lawphil lacks is read there)

Revision ID: s0005
Revises: s0004
"""
from alembic import op
import sqlalchemy as sa

revision = 's0005'
down_revision = 's0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('catalog_entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source', sa.String(16), server_default='lawphil', nullable=False))
        batch_op.create_index('ix_catalog_entries_source_year_month', ['source', 'year', 'month'], unique=False)
        batch_op.create_index('ix_catalog_entries_link_number_source', ['link_number', 'source', 'decision_date'], unique=False)
    # SQLite cannot change a primary key in place: the table is copied with (source, year, month) as its key.
    op.create_table(
        'catalog_months_new',
        sa.Column('source', sa.String(16), server_default='lawphil', nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('entries', sa.Integer(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('source', 'year', 'month'),
    )
    op.execute("INSERT INTO catalog_months_new (source, year, month, status, entries, read_at) "
               "SELECT 'lawphil', year, month, status, entries, read_at FROM catalog_months")
    op.drop_table('catalog_months')
    op.rename_table('catalog_months_new', 'catalog_months')


def downgrade() -> None:
    op.create_table(
        'catalog_months_old',
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('entries', sa.Integer(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('year', 'month'),
    )
    op.execute("INSERT INTO catalog_months_old (year, month, status, entries, read_at) "
               "SELECT year, month, status, entries, read_at FROM catalog_months WHERE source = 'lawphil'")
    op.drop_table('catalog_months')
    op.rename_table('catalog_months_old', 'catalog_months')
    op.execute("DELETE FROM catalog_entries WHERE source <> 'lawphil'")
    with op.batch_alter_table('catalog_entries', schema=None) as batch_op:
        batch_op.drop_index('ix_catalog_entries_link_number_source')
        batch_op.drop_index('ix_catalog_entries_source_year_month')
        batch_op.drop_column('source')
