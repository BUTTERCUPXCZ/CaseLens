"""The few queries that PostgreSQL and SQLite write differently. The web version runs on PostgreSQL, the desktop app on SQLite;
the repositories call these helpers so both get the same answers."""
from collections.abc import Sequence

from sqlalchemy import Integer, String, any_, exists, func, literal, literal_column, or_, select, type_coerce
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement


def dialect_of(session: Session) -> str:
    return session.get_bind().dialect.name


def insert_for(session: Session):
    """An INSERT that supports ON CONFLICT on both databases."""
    return postgresql.insert if dialect_of(session) == "postgresql" else sqlite.insert


def _as_array(column):
    """On PostgreSQL the list column is a real ARRAY (see `orm_models.ListOf`); say so, so its array operators are available."""
    return type_coerce(column, postgresql.ARRAY(String))


def _json_values(column):
    return func.json_each(column).table_valued("value")


def list_contains(session: Session, column, value: str) -> ColumnElement[bool]:
    """`value` is one of the items of a list column (`cases.numbers`)."""
    if dialect_of(session) == "postgresql":
        return literal(value) == any_(_as_array(column))
    items = _json_values(column)
    return exists(select(literal_column("1")).select_from(items).where(items.c.value == value))


def list_overlaps(session: Session, column, values: Sequence[str]) -> ColumnElement[bool]:
    """The list column shares at least one item with `values`."""
    if dialect_of(session) == "postgresql":
        return _as_array(column).overlap(list(values))
    items = _json_values(column)
    return exists(select(literal_column("1")).select_from(items).where(items.c.value.in_(list(values))))


def year_of(session: Session, column) -> ColumnElement[int]:
    """The year of a date column, as a number."""
    if dialect_of(session) == "postgresql":
        return func.extract("year", column).cast(Integer)
    return func.strftime("%Y", column).cast(Integer)


__all__ = ["dialect_of", "insert_for", "list_contains", "list_overlaps", "year_of", "or_"]
