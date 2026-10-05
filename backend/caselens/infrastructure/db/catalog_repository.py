from datetime import date

from sqlalchemy import and_, case, delete, exists, func, or_, select
from sqlalchemy.orm import Session

from caselens.application.ports.catalog import CatalogRepository
from caselens.domain.entities import CatalogEntry, CatalogHit, CatalogStatus, IndexPage
from caselens.domain.services.catalog_query import CatalogQuery
from caselens.domain.value_objects import GrNumber
from caselens.infrastructure.db.orm_models import (
    CaseModel,
    CatalogEntryModel,
    CatalogMonthModel,
    CatalogNumberModel,
)


def _number_spellings(number: str) -> list[str]:
    """Old cases are printed `L-28156`, but students usually type `28156`: look for both."""
    return [number, f"L-{number}"] if number.isdigit() else [number]


def _escape_like(text: str) -> str:
    """Make the student's own % and _ literal characters instead of wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlCatalogRepository(CatalogRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- writing ------------------------------------------------------------------

    def replace_month(self, page: IndexPage, entries: list[CatalogEntry], broken: bool = False) -> None:
        # Delete and re-insert inside one transaction: reading a month again (the current
        # month is re-read daily) never duplicates rows, and a crash never leaves half a month.
        self._session.execute(
            delete(CatalogEntryModel).where(
                CatalogEntryModel.year == page.year, CatalogEntryModel.month == page.month
            )
        )
        seen: set[tuple[str, str]] = set()
        for entry in entries:
            label_key = " ".join(entry.numbers)
            if (entry.source_url, label_key) in seen:  # the same row printed twice on one page
                continue
            seen.add((entry.source_url, label_key))
            model = CatalogEntryModel(
                source_url=entry.source_url,
                link_number=entry.gr_no.value,
                label_key=label_key,
                title=entry.title,
                decision_date=entry.decision_date,
                year=page.year,
                month=page.month,
                index_url=entry.index_url,
            )
            model.numbers = [CatalogNumberModel(number=number) for number in entry.numbers]
            self._session.add(model)

        self._session.merge(
            CatalogMonthModel(
                year=page.year,
                month=page.month,
                status="broken" if broken else "read",
                entries=len(seen),
                read_at=func.now(),
            )
        )
        self._session.commit()

    def mark_absent(self, page: IndexPage) -> None:
        self._session.merge(
            CatalogMonthModel(year=page.year, month=page.month, status="absent", entries=0, read_at=func.now())
        )
        self._session.commit()

    def register_months(self, pages: list[IndexPage]) -> None:
        existing = {(m.year, m.month) for m in self._session.scalars(select(CatalogMonthModel))}
        for page in pages:
            if (page.year, page.month) not in existing:
                self._session.add(CatalogMonthModel(year=page.year, month=page.month, status="pending", entries=0))
        self._session.commit()

    def read_months(self) -> set[tuple[int, int]]:
        rows = self._session.execute(
            select(CatalogMonthModel.year, CatalogMonthModel.month).where(CatalogMonthModel.status == "read")
        )
        return {(r.year, r.month) for r in rows}

    # -- searching ----------------------------------------------------------------

    def search(
        self, query: CatalogQuery, year: int | None, limit: int, offset: int
    ) -> tuple[list[CatalogHit], int]:
        if query.is_empty:
            return [], 0
        conditions = self._conditions(query, year)
        total = self._session.scalar(select(func.count()).select_from(CatalogEntryModel).where(*conditions)) or 0
        rows = self._session.execute(
            select(CatalogEntryModel, CaseModel.id.label("case_id"))
            .outerjoin(CaseModel, CaseModel.source_url == CatalogEntryModel.source_url)
            .where(*conditions)
            .order_by(
                self._exact_first(query),
                CatalogEntryModel.year.desc(),
                CatalogEntryModel.month.desc(),
                CatalogEntryModel.decision_date.desc().nulls_last(),
                CatalogEntryModel.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        ).all()
        return [CatalogHit(self._entity(model), case_id) for model, case_id in rows], total

    @staticmethod
    def _exact_first(query: CatalogQuery):
        """A typed number matches by prefix ("1800" finds 180046), but a row that has exactly
        that number must come before rows that merely start with it."""
        if query.number is None:
            return case((CatalogEntryModel.id.is_not(None), 0))  # constant: no effect for name searches
        exact = exists().where(
            and_(
                CatalogNumberModel.entry_id == CatalogEntryModel.id,
                CatalogNumberModel.number.in_(_number_spellings(query.number)),
            )
        )
        return case((exact, 0), else_=1)

    @staticmethod
    def _conditions(query: CatalogQuery, year: int | None) -> list:
        conditions = []
        if year is not None:
            conditions.append(CatalogEntryModel.year == year)
        if query.number is not None:
            prefixes = [f"{_escape_like(spelling)}%" for spelling in _number_spellings(query.number)]
            conditions.append(
                exists().where(
                    and_(
                        CatalogNumberModel.entry_id == CatalogEntryModel.id,
                        or_(*[CatalogNumberModel.number.like(prefix, escape="\\") for prefix in prefixes]),
                    )
                )
            )
        for word in query.words:  # every word must appear somewhere in the case name
            conditions.append(CatalogEntryModel.title.ilike(f"%{_escape_like(word)}%", escape="\\"))
        return conditions

    def find_by_number(self, gr_no: GrNumber) -> list[CatalogEntry]:
        models = self._session.scalars(
            select(CatalogEntryModel)
            .join(CatalogNumberModel, CatalogNumberModel.entry_id == CatalogEntryModel.id)
            .where(CatalogNumberModel.number == gr_no.value)
            .order_by(CatalogEntryModel.decision_date.desc().nulls_last(), CatalogEntryModel.id.desc())
        )
        return [self._entity(model) for model in models]

    def unsaved(self, first_year: int, last_year: int, after_id: int, limit: int) -> list[tuple[int, str]]:
        saved = select(CaseModel.id).where(CaseModel.source_url == CatalogEntryModel.source_url).exists()
        rows = self._session.execute(
            select(func.min(CatalogEntryModel.id).label("cursor"), CatalogEntryModel.source_url)
            .where(CatalogEntryModel.year.between(first_year, last_year), ~saved)
            .group_by(CatalogEntryModel.source_url)
            .having(func.min(CatalogEntryModel.id) > after_id)
            .order_by("cursor")
            .limit(limit)
        )
        return [(r.cursor, r.source_url) for r in rows]

    def status(self, building: bool) -> CatalogStatus:
        entries = self._session.scalar(select(func.count()).select_from(CatalogEntryModel)) or 0
        known = self._session.scalar(select(func.count()).select_from(CatalogMonthModel)) or 0
        # "handled" = read, or checked and absent: a month Lawphil lists but does not serve
        # must not leave the catalog looking unfinished forever.
        read = self._session.scalar(
            select(func.count()).select_from(CatalogMonthModel).where(CatalogMonthModel.status.in_(("read", "absent")))
        ) or 0
        if building:
            state = "building"
        elif entries == 0:
            state = "empty"
        elif read < known:
            state = "partial"
        else:
            state = "ready"
        return CatalogStatus(entries=entries, months_read=read, months_known=known, state=state)

    @staticmethod
    def _entity(model: CatalogEntryModel) -> CatalogEntry:
        numbers = tuple(model.label_key.split(" ")) if model.label_key else ()
        return CatalogEntry(
            gr_no=GrNumber(model.link_number),
            numbers=numbers,
            title=model.title,
            decision_date=model.decision_date if isinstance(model.decision_date, date) else None,
            source_url=model.source_url,
            index_url=model.index_url,
        )
