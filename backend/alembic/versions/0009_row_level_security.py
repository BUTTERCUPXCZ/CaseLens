"""turn on Row Level Security for every table, with no policies

Revision ID: 0009
Revises: 0008

Supabase puts a public REST API in front of every table in the `public` schema. With RLS on and no policy,
that API (the anon and authenticated roles) sees nothing. The backend connects as the table owner, which is
not subject to RLS, so the application is not affected. On a plain PostgreSQL it changes nothing visible.
A table added later needs its own `ENABLE ROW LEVEL SECURITY` in its migration.
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE t record;
        BEGIN
            FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE t record;
        BEGIN
            FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t.tablename);
            END LOOP;
        END $$;
        """
    )
