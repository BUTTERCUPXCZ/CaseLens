import pytest

from caselens.infrastructure.config import Settings
from caselens.infrastructure.db.session import _connect_args


@pytest.mark.parametrize("given", ["postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"])
def test_every_database_address_form_uses_psycopg(given):
    assert Settings(database_url=given).database_url == "postgresql+psycopg://u:p@h:5432/db"


def test_a_blank_access_code_means_no_gate():
    assert Settings(access_code="  ").access_code is None
    assert Settings(access_code=" abc ").access_code == "abc"


def test_a_hosted_database_requires_ssl_and_a_local_one_does_not():
    assert _connect_args("postgresql+psycopg://u:p@aws-0-ap.pooler.supabase.com:5432/postgres") == {"sslmode": "require"}
    assert _connect_args("postgresql+psycopg://u:p@localhost:5434/db") == {}
    assert _connect_args("postgresql+psycopg://u:p@db:5432/db") == {}


def test_a_sslmode_already_in_the_url_is_not_overridden():
    assert _connect_args("postgresql+psycopg://u:p@aws.pooler.supabase.com:5432/postgres?sslmode=verify-full") == {}
