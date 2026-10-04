"""Translate between persistence models (SQLAlchemy) and domain entities.

Keeping this in one place is what lets the domain stay free of SQLAlchemy.
"""
from caselens.domain.entities import (
    Case,
    CitedCase,
    Footnote,
    Opinion,
    Statute,
    Upload,
    UploadedCitation,
)
from caselens.domain.value_objects import (
    ClaimedCitation,
    Disposition,
    DocType,
    GrNumber,
    MatchStatus,
    StatuteType,
)
from caselens.infrastructure.db.orm_models import (
    CaseCitationModel,
    CaseFootnoteModel,
    CaseModel,
    CaseOpinionModel,
    CaseStatuteModel,
    UploadCitationModel,
    UploadModel,
)


def case_to_entity(model: CaseModel) -> Case:
    own_footnotes = [f for f in model.footnotes if f.opinion_id is None]
    opinions = [
        Opinion(
            kind=o.kind,
            author=o.author,
            text=o.text,
            footnotes=_footnotes([f for f in model.footnotes if f.opinion_id == o.id]),
        )
        for o in sorted(model.opinions, key=lambda o: o.id)
    ]
    return Case(
        id=model.id,
        gr_no=GrNumber(model.gr_no),
        source_url=model.source_url,
        title=model.title,
        decision_date=model.decision_date,
        doc_type=DocType(model.doc_type),
        ponente=model.ponente,
        division=model.division,
        disposition=Disposition(model.disposition) if model.disposition else Disposition.UNKNOWN,
        raw_html=model.raw_html,
        full_text=model.full_text,
        parser_version=model.parser_version,
        numbers=tuple(model.numbers or ()),
        fetched_at=model.fetched_at,
        footnotes=_footnotes(own_footnotes),
        opinions=opinions,
        statutes=[
            Statute(StatuteType(s.statute_type), s.number, s.raw)
            for s in sorted(model.statutes, key=lambda s: s.id)
        ],
        cited_cases=[
            CitedCase(c.cited_title, c.cited_gr_no, c.source, c.footnote_number)
            for c in sorted(model.citations, key=lambda c: c.id)
        ],
    )


def _footnotes(models: list[CaseFootnoteModel]) -> list[Footnote]:
    return [Footnote(f.number, f.anchor, f.text) for f in sorted(models, key=lambda f: f.id)]


def case_to_model(case: Case) -> tuple[CaseModel, list[tuple[CaseOpinionModel, Opinion]]]:
    model = CaseModel()
    return model, fill_case_model(model, case)


def fill_case_model(
    model: CaseModel, case: Case
) -> list[tuple[CaseOpinionModel, Opinion]]:
    """Copy a parsed case onto a model, replacing its footnotes/statutes/citations/opinions.

    Returns (opinion model, opinion) pairs: opinion footnotes can only be attached after
    the opinions have database ids, so the repository does that step."""
    model.gr_no = str(case.gr_no)
    model.title = case.title
    model.decision_date = case.decision_date
    model.doc_type = case.doc_type.value
    model.ponente = case.ponente
    model.division = case.division
    model.disposition = case.disposition.value
    model.source_url = case.source_url
    model.raw_html = case.raw_html
    model.full_text = case.full_text
    model.parser_version = case.parser_version
    model.numbers = list(case.numbers)
    model.footnotes = [CaseFootnoteModel(number=f.number, anchor=f.anchor, text=f.text) for f in case.footnotes]
    model.statutes = [
        CaseStatuteModel(statute_type=s.statute_type.value, number=s.number, raw=s.raw)
        for s in case.statutes
    ]
    model.citations = [
        CaseCitationModel(
            cited_title=c.title,
            cited_gr_no=c.gr_no,
            source=c.source,
            footnote_number=c.footnote_number,
        )
        for c in case.cited_cases
    ]
    opinion_pairs = [
        (CaseOpinionModel(kind=o.kind, author=o.author, text=o.text), o) for o in case.opinions
    ]
    model.opinions = [pair[0] for pair in opinion_pairs]
    return opinion_pairs


def upload_to_entity(model: UploadModel) -> Upload:
    return Upload(
        id=model.id,
        filename=model.filename,
        text=model.text,
        status=model.status,
        created_at=model.created_at,
        citations=[citation_to_entity(c) for c in sorted(model.citations, key=lambda c: c.id)],
    )


def citation_to_entity(model: UploadCitationModel) -> UploadedCitation:
    return UploadedCitation(
        id=model.id,
        claimed=ClaimedCitation(
            gr_number=GrNumber(model.gr_no),
            raw=model.raw_citation,
            title=model.claimed_title,
            claimed_date=model.claimed_date,
            claimed_year=model.claimed_year,
            reporter=model.reporter,
        ),
        status=MatchStatus(model.status),
        matched_case_id=model.matched_case_id,
        mismatches=model.mismatches or {},
        unverified=model.unverified or [],
        message=model.message,
    )


def citation_to_model(entity: UploadedCitation) -> UploadCitationModel:
    claimed = entity.claimed
    model = UploadCitationModel(
        raw_citation=claimed.raw,
        gr_no=str(claimed.gr_number),
        claimed_year=claimed.claimed_year,
        claimed_title=claimed.title,
        claimed_date=claimed.claimed_date,
        reporter=claimed.reporter,
    )
    apply_result(model, entity)
    return model


def apply_result(model: UploadCitationModel, entity: UploadedCitation) -> None:
    model.status = entity.status.value
    model.matched_case_id = entity.matched_case_id
    model.mismatches = entity.mismatches
    model.unverified = entity.unverified
    model.message = entity.message
