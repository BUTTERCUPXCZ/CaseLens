"""settings changed from the website's Settings page (which OpenRouter model writes the digests)

Revision ID: 0018
Revises: 0017
"""
import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY")  # Supabase exposes public tables: see 0009


def downgrade() -> None:
    op.drop_table("app_settings")
