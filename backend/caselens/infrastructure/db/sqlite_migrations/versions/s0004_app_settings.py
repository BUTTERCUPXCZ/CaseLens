"""settings changed from the website's Settings page (which OpenRouter model writes the digests)

Revision ID: s0004
Revises: s0003
"""
from alembic import op
import sqlalchemy as sa

revision = 's0004'
down_revision = 's0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'app_settings',
        sa.Column('key', sa.String(64), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('app_settings')
