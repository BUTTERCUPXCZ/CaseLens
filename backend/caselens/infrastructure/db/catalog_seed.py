"""The catalog (Lawphil's and the SC E-Library's monthly lists) ships inside the desktop app and the website's image as
`catalog.sqlite`, so search works on the first start without a build. `export_catalog` makes that file from a filled database;
`import_catalog` copies in each library's rows the catalog does not have yet (into SQLite or PostgreSQL)."""
import logging
import sqlite3
import sys
import threading
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import Engine, delete, func, insert, select, text

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
        # The file is only read row by row when copied in, so its indexes are dead weight: drop them before shipping it.
        for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL").fetchall():
            connection.execute(f'DROP INDEX "{name}"')
        connection.execute("PRAGMA journal_mode=DELETE")  # one self-contained file to ship
        connection.execute("VACUUM")
    return count


def import_catalog(engine: Engine, seed_path: Path) -> int:
    """Copy into the catalog each library's list (Lawphil, the SC E-Library) that the shipped file has and the catalog does not.
    A fresh library gets both; one that already has Lawphil's (an update) gets only the E-Library's. Returns the rows copied.
    Works on SQLite and PostgreSQL. An older file without a `source` column is all Lawphil."""
    if not seed_path.exists():
        return 0
    with sqlite3.connect(f"file:{seed_path.as_posix()}?mode=ro", uri=True) as seed:
        seed.row_factory = sqlite3.Row
        has_source = "source" in {row["name"] for row in seed.execute("PRAGMA table_info(catalog_entries)")}
        in_seed = [r[0] for r in seed.execute("SELECT DISTINCT source FROM catalog_entries")] if has_source else ["lawphil"]
        entries_table, numbers_table, months_table = (t.__table__ for t in (CatalogEntryModel, CatalogNumberModel, CatalogMonthModel))
        with engine.connect() as connection:
            present = set(connection.scalars(select(entries_table.c.source).distinct()))
        missing = [source for source in in_seed if source not in present]
        if not missing:
            return 0
        copied = 0
        with engine.begin() as write:
            entry_offset = write.scalar(select(func.coalesce(func.max(entries_table.c.id), 0)))
            number_offset = write.scalar(select(func.coalesce(func.max(numbers_table.c.id), 0)))
            for source in missing:
                where = "WHERE source = ?" if has_source else "WHERE ? = ?"
                args = (source,) if has_source else ("lawphil", "lawphil")
                rows = seed.execute(f"SELECT * FROM catalog_entries {where}", args)
                while batch := rows.fetchmany(_BATCH):
                    write.execute(insert(entries_table), [
                        {**{c: row[c] for c in row.keys() if c in entries_table.c}, "id": row["id"] + entry_offset, "source": source,
                         "decision_date": _day(row["decision_date"])} for row in batch
                    ])
                    copied += len(batch)
                rows = seed.execute(
                    f"SELECT n.id, n.entry_id, n.number FROM catalog_numbers n JOIN catalog_entries e ON e.id = n.entry_id {where.replace('source', 'e.source')}",
                    args,
                )
                while batch := rows.fetchmany(_BATCH):
                    write.execute(insert(numbers_table), [
                        {"id": row["id"] + number_offset, "entry_id": row["entry_id"] + entry_offset, "number": row["number"]} for row in batch
                    ])
                write.execute(delete(months_table).where(months_table.c.source == source))  # months a started build only registered
                months = seed.execute(f"SELECT * FROM catalog_months {where}", args).fetchall()
                if months:
                    write.execute(insert(months_table), [
                        {"source": source, "year": m["year"], "month": m["month"], "status": m["status"], "entries": m["entries"],
                         "read_at": _moment(m["read_at"])} for m in months
                    ])
            if engine.dialect.name == "postgresql":  # move each id counter past the copied ids, so later inserts do not collide
                for table in (entries_table, numbers_table):
                    write.execute(text(f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), COALESCE((SELECT max(id) FROM {table.name}), 1))"))
    log.info("Catalog filled from the shipped list: %s cases from %s", copied, ", ".join(missing))
    return copied


def _day(value) -> date | None:
    return date.fromisoformat(value[:10]) if isinstance(value, str) and value else value


def _moment(value) -> datetime | None:
    if isinstance(value, str) and value:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    return value


SHIPPED_SEED = Path(__file__).resolve().parents[3] / "catalog.sqlite"  # backend/catalog.sqlite (/srv/catalog.sqlite in the image)


def seed_catalog_in_background(engine: Engine, seed_path: Path = SHIPPED_SEED) -> threading.Thread:
    """The website: fill the catalog from the shipped file on a background thread (each library it lacks), so the site answers at once. It holds the
    catalog-build lock meanwhile, so a search does not start the 8-minute build in parallel, and two starts never copy twice."""
    from caselens.infrastructure.db.job_lock_repository import SqlJobLockRepository
    from caselens.infrastructure.queue import lock_keys

    def run() -> None:
        locks = SqlJobLockRepository(engine)
        if not locks.acquire(lock_keys.CATALOG_BUILD_KEY, lock_keys.CATALOG_BUILD_LOCK_SECONDS):
            return  # a build or another copy is already running
        try:
            import_catalog(engine, seed_path)
        except Exception:
            log.exception("could not fill the catalog from %s; a search will build it instead", seed_path)
        finally:
            locks.release(lock_keys.CATALOG_BUILD_KEY)

    thread = threading.Thread(target=run, name="catalog-seed", daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":  # python -m caselens.infrastructure.db.catalog_seed <database url> <out file>
    print(export_catalog(sys.argv[1], Path(sys.argv[2])))
