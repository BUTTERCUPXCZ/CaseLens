import re

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from collections.abc import Sequence

from caselens.application.ports.repositories import (
    CaseRepository,
    MonthIndexRepository,
    SubjectRepository,
    UnitOfWork,
    UploadRepository,
)
from caselens.domain.entities import Case, CaseSummary, Upload, UploadSummary
from caselens.domain.errors import DuplicateCaseError
from caselens.domain.subjects import Subject, SubjectCount
from caselens.domain.value_objects import Disposition, DocType, GrNumber, MatchStatus
from caselens.infrastructure.db import mappers
from caselens.infrastructure.db.portable import insert_for, list_contains, list_overlaps
from caselens.infrastructure.db.orm_models import (
    CaseFootnoteModel,
    CaseModel,
    CaseSubjectModel,
    MonthIndexModel,
    SubjectModel,
    UploadCitationModel,
    UploadModel,
)

_SUMMARY_COLUMNS = (
    CaseModel.id,
    CaseModel.gr_no,
    CaseModel.title,
    CaseModel.decision_date,
    CaseModel.doc_type,
    CaseModel.ponente,
    CaseModel.division,
    CaseModel.disposition,
    CaseModel.source_url,
    CaseModel.main_case_id,
    CaseModel.numbers,
)


def _select_summaries():
    """The columns of a case list; the large text and page are never loaded (the tags are added by `_with_tags`)."""
    return select(*_SUMMARY_COLUMNS).select_from(CaseModel)


def _summary(row, tags: dict[int, tuple[Subject, ...]]) -> CaseSummary:
    return CaseSummary(
        id=row.id,
        gr_no=GrNumber(row.gr_no),
        title=row.title,
        decision_date=row.decision_date,
        doc_type=DocType(row.doc_type),
        ponente=row.ponente,
        division=row.division,
        disposition=Disposition(row.disposition) if row.disposition else Disposition.UNKNOWN,
        source_url=row.source_url,
        subjects=tags.get(row.id, ()),
        main_case_id=row.main_case_id,
        numbers=tuple(row.numbers or ()),
    )


_GR_LABEL = re.compile(r"^\s*g\.?\s?r\.?\s*(?:nos?\.?)?\s*", re.IGNORECASE)


def _escape_like(text: str) -> str:
    """Make the user's own % and _ literal characters instead of wildcards."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _contains(text: str) -> str:
    return f"%{_escape_like(text)}%"


def _starts_with(text: str) -> str:
    return f"{_escape_like(text)}%"


def _tags_of(session: Session, case_ids: list[int]) -> dict[int, tuple[Subject, ...]]:
    """The tags of these cases, each in the list's order."""
    if not case_ids:
        return {}
    rows = session.execute(
        select(CaseSubjectModel.case_id, SubjectModel.id, SubjectModel.name)
        .join(SubjectModel, SubjectModel.id == CaseSubjectModel.subject_id)
        .where(CaseSubjectModel.case_id.in_(case_ids))
        .order_by(SubjectModel.sort_order)
    )
    tags: dict[int, list[Subject]] = {}
    for case_id, subject_id, name in rows:
        tags.setdefault(case_id, []).append(Subject(subject_id, name))
    return {k: tuple(v) for k, v in tags.items()}


def _with_tags(session: Session, rows) -> list[CaseSummary]:
    rows = list(rows)
    tags = _tags_of(session, [r.id for r in rows])
    return [_summary(r, tags) for r in rows]


class SqlMonthIndexRepository(MonthIndexRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, url: str) -> list[str] | None:
        row = self._session.get(MonthIndexModel, url)
        return list(row.links) if row else None

    def save(self, url: str, case_urls: list[str]) -> None:
        # Cache writes are idempotent and independent of the caller's other work, so
        # they commit immediately: a crawl that dies midway keeps what it already fetched.
        self._session.merge(MonthIndexModel(url=url, links=case_urls))
        self._session.commit()


class SqlCaseRepository(CaseRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, case: Case) -> Case:
        model, opinion_pairs = mappers.case_to_model(case)
        try:
            with self._session.begin_nested():  # savepoint: a duplicate must not poison the session
                self._session.add(model)
                self._session.flush()
        except IntegrityError as exc:
            raise DuplicateCaseError(case.source_url) from exc

        self._add_opinion_footnotes(model, opinion_pairs)
        self._session.refresh(model)
        return mappers.case_to_entity(model)

    def _add_opinion_footnotes(self, model: CaseModel, opinion_pairs) -> None:
        for opinion_model, opinion in opinion_pairs:
            for footnote in opinion.footnotes:
                self._session.add(
                    CaseFootnoteModel(
                        case_id=model.id,
                        opinion_id=opinion_model.id,
                        number=footnote.number,
                        anchor=footnote.anchor,
                        text=footnote.text,
                    )
                )
        self._session.flush()

    def outdated(self, current_parser_version: int) -> list[tuple[int, str, str]]:
        rows = self._session.execute(
            select(CaseModel.id, CaseModel.source_url, CaseModel.raw_html)
            .where(CaseModel.parser_version < current_parser_version)
            .order_by(CaseModel.id)
        )
        return [(r.id, r.source_url, r.raw_html) for r in rows]

    def with_damaged_text(self) -> list[tuple[int, str]]:
        rows = self._session.execute(
            select(CaseModel.id, CaseModel.source_url)
            .where(CaseModel.raw_html.contains("\ufffd"))
            .order_by(CaseModel.id)
        )
        return [(r.id, r.source_url) for r in rows]

    def update_content(self, case_id: int, parsed: Case) -> None:
        model = self._session.get(CaseModel, case_id)
        opinion_pairs = mappers.fill_case_model(model, parsed)
        self._session.flush()  # gives the new opinions their ids
        self._add_opinion_footnotes(model, opinion_pairs)

    def get(self, case_id: int) -> Case | None:
        model = self._session.get(CaseModel, case_id)
        return mappers.case_to_entity(model) if model else None

    def get_by_source_url(self, url: str) -> Case | None:
        model = self._session.scalar(select(CaseModel).where(CaseModel.source_url == url))
        return mappers.case_to_entity(model) if model else None

    def find_by_gr_no(self, gr_no: GrNumber) -> list[Case]:
        # By the page's own first number, or by any number a joint decision prints.
        models = self._session.scalars(
            select(CaseModel)
            .where(or_(CaseModel.gr_no == str(gr_no), list_contains(self._session, CaseModel.numbers, str(gr_no))))
            .order_by(CaseModel.id)
        )
        return [mappers.case_to_entity(m) for m in models]

    def search(
        self, query: str | None, limit: int, offset: int, subject_id: int | None = None, no_subject: bool = False
    ) -> tuple[list[CaseSummary], int]:
        conditions = [CaseModel.main_case_id.is_(None)]  # one row per case: a related page (a Resolution, a repeat) is not listed
        if query:
            gr_part = _GR_LABEL.sub("", query).strip() or query  # "G.R. No. 1800" -> "1800"
            conditions.append(
                or_(
                    CaseModel.title.ilike(_contains(query), escape="\\"),
                    CaseModel.gr_no.ilike(_starts_with(gr_part), escape="\\"),
                )
            )
        tagged = select(CaseSubjectModel.case_id).where(CaseSubjectModel.case_id == CaseModel.id)
        if subject_id is not None:
            conditions.append(tagged.where(CaseSubjectModel.subject_id == subject_id).exists())
        elif no_subject:
            conditions.append(~tagged.exists())
        total = self._session.scalar(select(func.count()).select_from(CaseModel).where(*conditions)) or 0
        rows = self._session.execute(
            _select_summaries()
            .where(*conditions)
            .order_by(CaseModel.decision_date.desc().nulls_last(), CaseModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return _with_tags(self._session, rows), total

    def summaries(self, case_ids: list[int]) -> dict[int, CaseSummary]:
        if not case_ids:
            return {}
        rows = self._session.execute(_select_summaries().where(CaseModel.id.in_(case_ids)))
        return {s.id: s for s in _with_tags(self._session, rows)}

    def find_overlapping(self, numbers: Sequence[str]) -> list[CaseSummary]:
        wanted = list(dict.fromkeys(numbers))
        if not wanted:
            return []
        rows = self._session.execute(
            _select_summaries().where(or_(list_overlaps(self._session, CaseModel.numbers, wanted), CaseModel.gr_no.in_(wanted))).order_by(CaseModel.id)
        )
        return _with_tags(self._session, rows)

    def set_main_case(self, case_ids: Sequence[int], main_case_id: int | None) -> None:
        ids = [i for i in case_ids if i != main_case_id]  # a case is never its own main case
        if ids:
            self._session.execute(update(CaseModel).where(CaseModel.id.in_(ids)).values(main_case_id=main_case_id))
        if main_case_id is not None:
            self._session.execute(update(CaseModel).where(CaseModel.id == main_case_id).values(main_case_id=None))
        self._session.flush()

    def add_subjects(self, case_id: int, subject_ids: Sequence[int], source: str) -> None:
        if subject_ids:
            self._session.execute(
                insert_for(self._session)(CaseSubjectModel)
                .values([{"case_id": case_id, "subject_id": i, "source": source} for i in dict.fromkeys(subject_ids)])
                .on_conflict_do_nothing(index_elements=["case_id", "subject_id"])
            )
        self._session.flush()
        self._session.expire_all()  # a loaded case shows its new tags

    def set_subjects(self, case_id: int, subject_ids: Sequence[int], source: str) -> None:
        self._session.execute(delete(CaseSubjectModel).where(CaseSubjectModel.case_id == case_id))
        self.add_subjects(case_id, subject_ids, source)

    def subject_counts(self) -> list[SubjectCount]:
        main = CaseModel.main_case_id.is_(None)
        counted = dict(
            self._session.execute(
                select(CaseSubjectModel.subject_id, func.count())
                .join(CaseModel, CaseModel.id == CaseSubjectModel.case_id)
                .where(main)
                .group_by(CaseSubjectModel.subject_id)
            ).all()
        )
        untagged = self._session.scalar(
            select(func.count()).select_from(CaseModel).where(main, ~select(CaseSubjectModel.case_id).where(CaseSubjectModel.case_id == CaseModel.id).exists())
        ) or 0
        subjects = self._session.scalars(select(SubjectModel).order_by(SubjectModel.sort_order)).all()
        return [SubjectCount(s.id, s.name, counted.get(s.id, 0)) for s in subjects] + [SubjectCount(None, "No subject yet", untagged)]


class SqlSubjectRepository(SubjectRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[Subject]:
        return [Subject(s.id, s.name) for s in self._session.scalars(select(SubjectModel).order_by(SubjectModel.sort_order))]

    def get(self, subject_id: int) -> Subject | None:
        model = self._session.get(SubjectModel, subject_id)
        return Subject(model.id, model.name) if model else None


class SqlUploadRepository(UploadRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, upload: Upload) -> Upload:
        model = UploadModel(filename=upload.filename, text=upload.text, file_data=upload.file_data, status=upload.status)
        model.citations = [mappers.citation_to_model(c) for c in upload.citations]
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)

        upload.id, upload.created_at = model.id, model.created_at
        for entity, citation_model in zip(upload.citations, model.citations):
            entity.id = citation_model.id
        return upload

    def get(self, upload_id: int) -> Upload | None:
        model = self._session.get(UploadModel, upload_id)
        return mappers.upload_to_entity(model) if model else None

    def get_file_data(self, upload_id: int) -> bytes | None:
        return self._session.scalar(select(UploadModel.file_data).where(UploadModel.id == upload_id))

    def delete(self, upload_id: int) -> bool:
        model = self._session.get(UploadModel, upload_id)
        if model is None:
            return False
        self._session.delete(model)  # its citations go with it; its digests are removed by the database (ON DELETE CASCADE)
        self._session.flush()
        return True

    def list_recent(self, limit: int) -> list[UploadSummary]:
        def count(status: MatchStatus):
            return func.count(UploadCitationModel.id).filter(UploadCitationModel.status == status.value)

        rows = self._session.execute(
            select(
                UploadModel.id,
                UploadModel.filename,
                UploadModel.status,
                UploadModel.created_at,
                count(MatchStatus.MATCH).label("matched"),
                count(MatchStatus.MISMATCH).label("needs_look"),
                count(MatchStatus.NOT_FOUND).label("not_found"),
                count(MatchStatus.ERROR).label("errors"),
                count(MatchStatus.PENDING).label("pending"),
            )
            .join(UploadCitationModel, UploadCitationModel.upload_id == UploadModel.id, isouter=True)
            .group_by(UploadModel.id)
            .order_by(UploadModel.created_at.desc(), UploadModel.id.desc())
            .limit(limit)
        )
        return [
            UploadSummary(
                id=r.id,
                filename=r.filename,
                status=r.status,
                created_at=r.created_at,
                matched=r.matched,
                needs_look=r.needs_look,
                not_found=r.not_found,
                errors=r.errors,
                pending=r.pending,
            )
            for r in rows
        ]

    def save(self, upload: Upload) -> None:
        model = self._session.get(UploadModel, upload.id)
        model.status = upload.status
        by_id = {c.id: c for c in model.citations}
        for citation in upload.citations:
            mappers.apply_result(by_id[citation.id], citation)
        self._session.flush()


class SqlUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()
