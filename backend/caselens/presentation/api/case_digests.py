import re
from dataclasses import replace
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel

from caselens.application.use_cases.build_digest_request import build_digest_header
from caselens.composition import Services
from caselens.domain.digest_v2 import LEVEL_SECTIONS, clean_scope, SECTION_TITLES, CaseDigestV2, DigestHeader, DigestState, Level, Section, sections_for
from caselens.domain.entities import Case
from caselens.domain.section_edits import section_text, with_edits
from caselens.infrastructure.ai.prompts.digest_v1 import DIGEST_VERSION
from caselens.presentation.dependencies import get_services

router = APIRouter(tags=["case digests"])

_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DigestSentenceOut(BaseModel):
    text: str
    key: bool = False  # a sentence not to miss: shown in bold, as in the client's sample
    cites: list[str]  # P12 = paragraph 12 of the decision; O2.5 = paragraph 5 of separate opinion 2; C1 = the case record


class DigestBlockOut(BaseModel):
    heading: str | None
    as_list: bool
    sentences: list[DigestSentenceOut]


class DigestSectionOut(BaseModel):
    key: str
    title: str
    blocks: list[DigestBlockOut]
    edited: bool = False  # the student rewrote it in this review (their text cites nothing)
    text: str  # the section as plain text, to start an edit from


class DigestHeaderOut(BaseModel):
    case_name: str
    citation: str
    topic: str | None
    ponente: str | None


class CaseDigestOut(BaseModel):
    id: int | None  # the digest; None until it is asked for
    case_id: int  # the MAIN case: a Resolution or a repeat of a case shows its main case's digest
    scope: str  # the topic scope this digest is focused on ("" = the standard digest)
    state: Literal["none", "pending", "ready", "failed"]  # none: not asked for yet
    error: str | None
    written: int
    dropped: int  # sentences the checks kept out (so a reader can see that nothing unbacked was filled in)
    header: DigestHeaderOut
    sections: list[DigestSectionOut]
    levels: dict[str, list[str]]  # which sections each download level prints
    updated_at: datetime | None
    current: bool = True  # written by the current prompt and checks; False: an older digest, kept until "Write it again"
    stage: Literal["queued", "writing", "checking", "repairing"] | None = None  # while pending: the step it is on (the progress bar)
    stage_seconds: int | None = None  # how long it has been on that step, counted here so a wrong clock on the reader's computer does not matter
    pending_seconds: int | None = None  # how long since it was asked for (a step does not touch `updated_at`, so that is when it was asked)

    @classmethod
    def build(cls, case: Case, digest: CaseDigestV2 | None, header: DigestHeader, edits: dict[Section, str] | None = None) -> "CaseDigestOut":
        sections = []
        if digest is not None:
            draft = with_edits(digest.draft, edits) if edits else digest.draft
            for section in LEVEL_SECTIONS[Level.FULL]:  # the page shows the full digest, Case Summary first
                blocks = draft.sections.get(section)
                if blocks:
                    sections.append(DigestSectionOut(
                        key=section.value, title=SECTION_TITLES[section], edited=bool(edits and section in edits), text=section_text(blocks),
                        blocks=[DigestBlockOut(heading=b.heading, as_list=b.as_list, sentences=[DigestSentenceOut(text=s.text, key=s.key, cites=list(s.cites)) for s in b.sentences]) for b in blocks],
                    ))
        return cls(
            id=digest.id if digest else None,
            case_id=case.main_case_id or case.id,
            scope=digest.scope if digest else "",
            state=digest.state.value if digest else "none",
            error=digest.error if digest else None,
            written=digest.written if digest else 0,
            dropped=digest.dropped if digest else 0,
            header=DigestHeaderOut(case_name=header.case_name, citation=header.citation, topic=header.topic, ponente=header.ponente),
            sections=sections,
            levels={level.value: [s.value for s in (sections_for(level, digest.draft) if digest else LEVEL_SECTIONS[level])] for level in Level},
            updated_at=digest.updated_at if digest else None,
            current=digest.is_current(DIGEST_VERSION) if digest else True,
            **_stage(digest),
        )


def _since(at: datetime | None) -> int:
    return max(0, int((datetime.now(UTC) - (at if at.tzinfo else at.replace(tzinfo=UTC))).total_seconds())) if at else 0


def _stage(digest: CaseDigestV2 | None) -> dict:
    if digest is None or digest.state is not DigestState.PENDING or digest.stage is None:
        return {}
    return {"stage": digest.stage.value, "stage_seconds": _since(digest.stage_at), "pending_seconds": _since(digest.updated_at)}


_SCOPE = Query("", max_length=300, description="The topic scope the digest is focused on; empty = the standard digest")


_BATCH = Query(None, description="The review (upload) the digest is read in: its section edits and its file's reporter citation apply")


def _topic(case: Case, scope: str) -> str | None:
    """The header's "Topic": the case's tags, then the scope the student asked for (as the client's sample: "Constitutional Law, Presidential Powers")."""
    parts = [s.name for s in case.subjects] + ([clean_scope(scope)] if clean_scope(scope) else [])
    return ", ".join(parts) or None


def _header(services: Services, case: Case, scope: str, batch_id: int | None) -> DigestHeader:
    header = build_digest_header(case, _topic(case, scope))
    reporter = services.review_reporter(batch_id, case.main_case_id or case.id) if batch_id is not None else None
    return replace(header, citation=f"{reporter}, {header.citation}") if reporter else header


def _edits(services: Services, digest: CaseDigestV2 | None, batch_id: int | None) -> dict[Section, str] | None:
    return services.review_edits(batch_id, digest.id) if batch_id is not None and digest is not None and digest.id is not None else None


def _out(services: Services, case: Case, digest: CaseDigestV2 | None, scope: str, batch_id: int | None = None) -> CaseDigestOut:
    return CaseDigestOut.build(case, digest, _header(services, case, scope, batch_id), _edits(services, digest, batch_id))


@router.get("/cases/{case_id}/case-digest", response_model=CaseDigestOut)
def get_case_digest(case_id: int, scope: str = _SCOPE, batch_id: int | None = _BATCH, services: Services = Depends(get_services)) -> CaseDigestOut:
    """The case digest in the client's format (Doctrine, Facts, Issue, Ruling, Ratio Decidendi, Dissents, Topic Explained, Why it matters)
    for a topic scope, or state "none" if it has not been asked for yet."""
    case, digest = services.get_case_digest_v2().execute(case_id, scope)
    return _out(services, case, digest, scope, batch_id)


@router.post("/cases/{case_id}/case-digest", response_model=CaseDigestOut, status_code=202)
def request_case_digest(
    case_id: int, regenerate: bool = False, scope: str = _SCOPE, batch_id: int | None = _BATCH, services: Services = Depends(get_services)
) -> CaseDigestOut:
    """Ask for the digest (for a topic scope, if given). It is written once in the background (a few minutes) and kept; poll GET until ready."""
    digest = services.request_case_digest_v2().execute(case_id, scope, regenerate)
    case, _ = services.get_case_digest_v2().execute(case_id, scope)
    return _out(services, case, digest, scope, batch_id)


@router.get("/cases/{case_id}/case-digest.docx")
def download_case_digest(
    case_id: int,
    level: Level = Query(Level.FULL, description="short: Case Summary and Doctrine; standard: Doctrine, Facts, Issue, Ruling; full: the whole digest"),
    sources: bool = Query(False, description="Print the decision paragraphs each part rests on (the client's sample does not)"),
    scope: str = _SCOPE,
    batch_id: int | None = _BATCH,
    services: Services = Depends(get_services),
) -> Response:
    """The digest as a Word file, laid out like the client's sample."""
    case, digest = services.get_case_digest_v2().execute(case_id, scope)
    if digest is None or digest.state.value != "ready":
        return Response(status_code=409, content=b'{"detail":"The digest is not ready yet."}', media_type="application/json")
    edits = _edits(services, digest, batch_id)
    draft = with_edits(digest.draft, edits) if edits else digest.draft
    data = services.case_digest_exporter().export(_header(services, case, scope, batch_id), draft, level, show_sources=sources)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", f"GR-{case.gr_no}-{level.value}-digest").strip("-")
    return Response(content=data, media_type=_DOCX, headers={"Content-Disposition": f'attachment; filename="{stem}.docx"'})


class SectionEditIn(BaseModel):
    text: str  # plain text: a blank line starts a paragraph, "- " a bullet, "# " a subheading; empty removes the section from this review


@router.put("/bulk/{batch_id}/digests/{digest_id}/sections/{section}", status_code=204)
def edit_section(batch_id: int, digest_id: int, section: Section, body: SectionEditIn, services: Services = Depends(get_services)) -> Response:
    """The student rewrites one section of a digest, in their review only. The shared AI digest is not changed."""
    services.edit_digest_section().save(batch_id, digest_id, section, body.text)
    return Response(status_code=204)


@router.delete("/bulk/{batch_id}/digests/{digest_id}/sections/{section}", status_code=204)
def put_back_section(batch_id: int, digest_id: int, section: Section, services: Services = Depends(get_services)) -> Response:
    """Put back the AI's text for this section in this review."""
    services.edit_digest_section().put_back(batch_id, digest_id, section)
    return Response(status_code=204)
