"""Trend queries as plain SQL: each one is a GROUP BY a reviewer can read and run in psql (or sqlite3, for the desktop app)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from caselens.application.ports.queries import InsightQueries
from caselens.domain.insights import (
    CitedCaseCount,
    DispositionCount,
    PonenteCount,
    StatuteCount,
)

_TOTAL = """
    SELECT COUNT(*) FROM cases WHERE doc_type = 'decision'
"""

_TOP_STATUTES = """
    SELECT s.statute_type, s.number, COUNT(DISTINCT s.case_id) AS cases
    FROM case_statutes s
    JOIN cases c ON c.id = s.case_id AND c.doc_type = 'decision'
    GROUP BY s.statute_type, s.number
    ORDER BY cases DESC, s.statute_type, s.number
    LIMIT :limit
"""

_DISPOSITIONS_BY_YEAR = """
    SELECT {year} AS year, disposition, COUNT(*) AS cases
    FROM cases
    WHERE doc_type = 'decision' AND decision_date IS NOT NULL
    GROUP BY year, disposition
    ORDER BY year, disposition
"""

# Same case cited under slightly different casing/spacing counts once. The few parts PostgreSQL and SQLite (the desktop app) write
# differently are filled in per database: {year} and {same_title}.
_DIALECT_PARTS = {
    "postgresql": {"year": "EXTRACT(YEAR FROM decision_date)::int", "same_title": "LOWER(REGEXP_REPLACE(cc.cited_title, '\\s+', ' ', 'g'))"},
    "sqlite": {
        "year": "CAST(strftime('%Y', decision_date) AS INTEGER)",
        "same_title": "LOWER(REPLACE(REPLACE(REPLACE(TRIM(cc.cited_title), '   ', ' '), '  ', ' '), '  ', ' '))",
    },
}
_MOST_CITED_CASES = """
    SELECT MIN(cc.cited_title) AS title,
           MAX(cc.cited_gr_no) AS gr_no,
           COUNT(DISTINCT cc.case_id) AS cases
    FROM case_citations cc
    JOIN cases c ON c.id = cc.case_id AND c.doc_type = 'decision'
    GROUP BY {same_title}
    ORDER BY cases DESC, title
    LIMIT :limit
"""

_CASES_PER_PONENTE = """
    SELECT ponente, COUNT(*) AS cases
    FROM cases
    WHERE doc_type = 'decision' AND ponente IS NOT NULL
    GROUP BY ponente
    ORDER BY cases DESC, ponente
    LIMIT :limit
"""


class SqlInsightQueries(InsightQueries):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _sql(self, template: str) -> str:
        parts = _DIALECT_PARTS["postgresql" if self._session.get_bind().dialect.name == "postgresql" else "sqlite"]
        return template.replace("{year}", parts["year"]).replace("{same_title}", parts["same_title"])

    def total_cases(self) -> int:
        return self._session.scalar(text(_TOTAL)) or 0

    def top_statutes(self, limit: int) -> list[StatuteCount]:
        rows = self._session.execute(text(_TOP_STATUTES), {"limit": limit})
        return [StatuteCount(r.statute_type, r.number, r.cases) for r in rows]

    def dispositions_by_year(self) -> list[DispositionCount]:
        rows = self._session.execute(text(self._sql(_DISPOSITIONS_BY_YEAR)))
        return [DispositionCount(r.year, r.disposition, r.cases) for r in rows]

    def most_cited_cases(self, limit: int) -> list[CitedCaseCount]:
        rows = self._session.execute(text(self._sql(_MOST_CITED_CASES)), {"limit": limit})
        return [CitedCaseCount(r.title, r.gr_no, r.cases) for r in rows]

    def cases_per_ponente(self, limit: int) -> list[PonenteCount]:
        rows = self._session.execute(text(_CASES_PER_PONENTE), {"limit": limit})
        return [PonenteCount(r.ponente, r.cases) for r in rows]
