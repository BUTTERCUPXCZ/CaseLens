"""The Lawphil catalog (about 35,000 rows) ships inside the desktop app as `catalog.sqlite`, so search works on the first start
without an 8-minute build. `export_catalog` makes that file from a filled database; `import_catalog` copies it in once."""
import logging
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import Engine, func, insert, select

from caselens.infrastructure.db.orm_models import CatalogEntryModel, CatalogMonthModel, CatalogNumberModel
from caselens.infrastructure.db.session import make_engine
from caselens.infrastructure.db.sqlite_schema import upgrade_sqlite

log = logging.getLogger(__name__)

# Parents before children (catalog_numbers points at catalog_entries).
_TABLES = [CatalogEntryModel.__table__, CatalogNumberModel.__table__, CatalogMonthModel.__table__]
_BATCH = 5000


def export_catalog(source_url: str, seed_path: Path) -> int:
    """Copy the catalog tables of any CaseLens database (PostgreSQL or SQLite) into a new SQLite file. Returns the entry count."""
    seed_path.unlink(missing_ok=True)
    seed_url = f"sqlite:///{seed_path.as_posix()}"
    upgrade_sqlite(seed_url)
    source, target = make_engine(source_url), make_engine(seed_url)
    with source.connect() as read, target.begin() as write:
        for table in _TABLES:
            rows = read.execute(select(table)).mappings()
            while batch := rows.fetchmany(_BATCH):
                write.execute(insert(table), [dict(row) for row in batch])
        count = write.execute(select(func.count()).select_from(CatalogEntryModel.__table__)).scalar_one()
    source.dispose()
    target.dispose()
    with sqlite3.connect(seed_path, isolation_level=None) as connection:  # outside any transaction, as SQLite requires
        connection.execute("PRAGMA journal_mode=DELETE")  # one self-contained file to ship
        connection.execute("VACUUM")
    return count


def import_catalog(engine: Engine, seed_path: Path) -> int:
    """Fill an empty catalog from the shipped file. Does nothing when the catalog already has rows or there is no file."""
    if not seed_path.exists():
        return 0
    with engine.connect() as connection:
        if connection.execute(select(func.count()).select_from(CatalogEntryModel.__table__)).scalar_one():
            return 0
    with sqlite3.connect(f"file:{seed_path.as_posix()}?mode=ro", uri=True):
        pass  # fails early on a missing or broken file
    # SQLite cannot ATTACH inside a transaction, so this uses the driver connection (it runs in autocommit mode) directly.
    raw = engine.raw_connection()
    try:
        cursor = raw.driver_connection.cursor()
        cursor.execute("ATTACH DATABASE ? AS seed", (str(seed_path),))
        try:
            cursor.execute("BEGIN")
            for table in _TABLES:
                columns = ", ".join(column.name for column in table.columns)
                cursor.execute(f"INSERT INTO main.{table.name} ({columns}) SELECT {columns} FROM seed.{table.name}")
            cursor.execute("COMMIT")
        except Exception:
            cursor.execute("ROLLBACK")
            raise
        finally:
            cursor.execute("DETACH DATABASE seed")
        count = cursor.execute(f"SELECT count(*) FROM {CatalogEntryModel.__tablename__}").fetchone()[0]
    finally:
        raw.close()
    log.info("Catalog filled from the shipped list: %s cases", count)
    return count


if __name__ == "__main__":  # python -m caselens.desktop.catalog_seed <database url> <out file>
    print(export_catalog(sys.argv[1], Path(sys.argv[2])))
