import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import UTC, datetime

from caselens.application.ports.ai import AnswerRequest
from caselens.application.ports.digests import DigestRepository
from caselens.application.ports.repositories import CaseRepository, UnitOfWork, UploadRepository
from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion, decision_sources
from caselens.application.use_cases.suggest_court_passages import PassageSuggestions, SuggestCourtPassages
from caselens.domain.case_digest import (
    CaseDigest,
    DigestField,
    DigestStatus,
    FieldKind,
    FieldOrigin,
    FieldState,
)
from caselens.domain.digest import GroundedAnswer, ParagraphRange, SourcePassage
from caselens.domain.errors import AiUnavailableError, CaseNotFoundError, DigestNotFoundError
from caselens.domain.services.digest_field_factory import DigestFieldFactory
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.reviewer_passage import ReviewerPassageFinder
from caselens.domain.services.ruling_locator import RulingLocator

logger = logging.getLogger(__name__)

_NO_ANSWERER = "Written explanations are not set up on this server."
_OVER_LIMIT = "The limit for written explanations today has been reached. Try again tomorrow."
_SERVICE_DOWN = "The explanation service did not answer. Try again in a moment."
_NOT_ENOUGH = "The decision does not say enough to answer this, so we left it empty."
_LOOK_FAILED = "We could not look for it just now. Press “Suggest for me” to try again, or pick the paragraphs yourself."
_LOOK_OVER_LIMIT = "The limit for suggestions today has been reached. Pick the paragraphs yourself, or try again tomorrow."


class BuildCaseDigest:
    """Writes the AI answers of a digest, one field at a time, saving after each so the student sees it appear.

    Runs in the background worker. The Court's own text was filled in when the digest was requested; here only
    the answer fields change. An answer that cannot be written (no key, daily limit, the service down, or the
    decision not saying enough) leaves the field empty with a plain reason. It is never filled with a guess.
    """

    def __init__(
        self,
        cases: CaseRepository,
        digests: DigestRepository,
        uploads: UploadRepository,
        uow: UnitOfWork,
        answerer: AnswerCaseQuestion | None,
        *,
        model: str = "",
        prompt_version: str = "",
        ai_allowed: Callable[[], bool] = lambda: True,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        sections: HeadingSections | None = None,
        rulings: RulingLocator | None = None,
        passages: ReviewerPassageFinder | None = None,
        parallel: int = 3,
        suggester: SuggestCourtPassages | None = None,
    ) -> None:
        self._suggester = suggester
        self._cases = cases
        self._digests = digests
        self._uploads = uploads
        self._uow = uow
        self._answerer = answerer
        self._model = model
        self._prompt_version = prompt_version
        self._ai_allowed = ai_allowed
        self._clock = clock
        self._sections = sections or HeadingSections()
        self._rulings = rulings or RulingLocator()
        self._passages = passages or ReviewerPassageFinder()
        self._parallel = max(1, parallel)

    def execute(self, digest_id: int, keys: list[str] | None = None) -> CaseDigest:
        digest = self._digests.get(digest_id)
        if digest is None:
            raise DigestNotFoundError(f"Digest {digest_id} does not exist.")
        case = self._cases.get(digest.case_id)
        if case is None:
            raise CaseNotFoundError(f"Case {digest.case_id} does not exist.")

        waiting = [
            f for f in digest.fields
            if (f.kind is FieldKind.ANSWER and ((keys is None and f.state is FieldState.PENDING) or (keys is not None and f.key in keys)))
            or (f.kind is FieldKind.VERBATIM and f.state is FieldState.PENDING and (keys is None or f.key in keys))  # a passage being looked for
        ]
        try:
            if waiting:
                self._write_answers(digest, waiting, case.full_text)
            digest.status, digest.error = DigestStatus.READY, None
        except Exception as exc:
            digest.status, digest.error = DigestStatus.FAILED, str(exc)[:300]
            self._digests.save(digest)
            self._uow.commit()
            raise
        self._digests.save(digest)
        self._uow.commit()
        return digest

    def _write_answers(self, digest: CaseDigest, waiting: list[DigestField], full_text: str) -> None:
        paragraphs = full_text.split("\n")
        start = self._sections.body_start(paragraphs)
        ruling = self._rulings.locate(paragraphs)
        sources: list[SourcePassage] = []
        if start is not None and ruling is not None:
            sources = self._context(digest) + decision_sources(paragraphs, start, ruling.last)

        # Fields that cannot be answered at all (no key, no text, over the daily limit) are settled here, in this thread.
        asks: list[DigestField] = []
        looking: list[DigestField] = []
        for item in waiting:
            if item.kind is FieldKind.VERBATIM:
                looking.append(item)
                continue
            refusal = self._refusal(item, sources)
            if refusal is not None:
                self._store(digest, refusal)
            else:
                asks.append(item)
        if looking and (self._suggester is None or not self._ai_allowed()):
            for item in looking:  # nothing to look with: settle at once with the plain way forward
                note = _LOOK_OVER_LIMIT if self._suggester is not None else None
                missing = DigestFieldFactory.missing(item.key)
                self._store(digest, replace(missing, note=note or missing.note))
            looking = []
        if not asks and not looking:
            return

        # The AI calls (each is a writer call, then a checker call) wait on the network and do not touch the database, so
        # they run side by side: two answers take as long as one. Saving stays in THIS thread (a database session is not
        # safe to share), and each answer is saved as soon as it is ready so the student sees it appear. Looking for the
        # Court's own passages (Facts, Issue, Doctrine) is one more such call, run beside the answers.
        with ThreadPoolExecutor(max_workers=max(1, min(len(asks) + (1 if looking else 0), self._parallel + 1))) as pool:
            futures: dict = {pool.submit(self._ask, item, sources): item for item in asks}
            if looking:
                keys = [item.key for item in looking]
                futures[pool.submit(self._look, keys, paragraphs, start, ruling)] = looking
            for future in as_completed(futures):
                item = futures[future]
                if isinstance(item, list):
                    self._settle_passages(digest, item, future.result(), paragraphs)
                else:
                    self._store(digest, self._field_from(item, future.result(), digest))

    def _look(self, keys: list[str], paragraphs: list[str], start: int | None, ruling: ParagraphRange | None) -> PassageSuggestions | None:
        """Ask for the Court's own passages. Runs in a worker thread: no database. None = the service is down."""
        assert self._suggester is not None
        try:
            return self._suggester.execute(keys, paragraphs, start, ruling)
        except AiUnavailableError:
            return None

    def _settle_passages(self, digest: CaseDigest, looking: list[DigestField], result: PassageSuggestions | None, paragraphs: list[str]) -> None:
        digest.ai_answered_at = self._clock()  # the look cost a call: it counts toward today's limit
        digest.model, digest.prompt_version = self._model, self._prompt_version
        for item in looking:
            if result is None:
                missing = DigestFieldFactory.missing(item.key)
                self._store(digest, replace(missing, note=_LOOK_FAILED))
                continue
            found = result.found.get(item.key)
            if found is None:
                self._store(digest, DigestFieldFactory.missing(item.key, searched=True))
            else:
                self._store(digest, DigestFieldFactory.suggested(item.key, item.label, found.range, paragraphs, found.reason))

    def _store(self, digest: CaseDigest, field: DigestField) -> None:
        digest.replace_field(field)
        self._digests.save(digest)
        self._uow.commit()

    @staticmethod
    def _unavailable(item: DigestField, why: str) -> DigestField:
        return DigestField(item.key, item.label, FieldKind.ANSWER, state=FieldState.UNAVAILABLE, question=item.question, note=why)

    def _refusal(self, item: DigestField, sources: list[SourcePassage]) -> DigestField | None:
        if self._answerer is None:
            return self._unavailable(item, _NO_ANSWERER)
        if not sources:
            return self._unavailable(item, _NOT_ENOUGH)
        if not self._ai_allowed():
            return self._unavailable(item, _OVER_LIMIT)
        return None

    def _ask(self, item: DigestField, sources: list[SourcePassage]) -> GroundedAnswer | None:
        """One question to the AI. Runs in a worker thread: it must not touch the database. None = the service is down."""
        assert self._answerer is not None  # `_refusal` already handled "no answerer"
        try:
            return self._answerer.answer(AnswerRequest(item.question or item.label, tuple(sources)))
        except AiUnavailableError:
            return None

    def _field_from(self, item: DigestField, answer: GroundedAnswer | None, digest: CaseDigest) -> DigestField:
        if answer is None:
            return self._unavailable(item, _SERVICE_DOWN)
        for sentence in answer.dropped:  # not shown to the student, but visible to whoever tunes the prompts
            logger.info("digest %s %s: dropped (%s): %s", digest.id, item.key, sentence.reason[:160], sentence.text[:200])
        digest.ai_answered_at = self._clock()
        digest.model, digest.prompt_version = self._model, self._prompt_version
        if answer.abstained:
            return self._unavailable(item, _NOT_ENOUGH)
        return DigestField(
            item.key,
            item.label,
            FieldKind.ANSWER,
            text="\n\n".join(s.text for s in answer.sentences),  # one sentence per paragraph: separate points, not a wall of text
            origin=FieldOrigin.AI_DRAFTED,
            state=FieldState.READY,
            cites=tuple(dict.fromkeys(cite for s in answer.sentences for cite in s.cites)),
            question=item.question,
        )

    def _context(self, digest: CaseDigest) -> list[SourcePassage]:
        """Passages that are not the decision: text the student pasted (S1..) and the reviewer's own paragraph (R1)."""
        context = [
            SourcePassage(f"S{n}", f.text)
            for n, f in enumerate((f for f in digest.fields if f.origin is FieldOrigin.STUDENT_PASTED and f.text), start=1)
        ]
        if digest.upload_id is not None:
            upload = self._uploads.get(digest.upload_id)
            citation = next(
                (c for c in (upload.citations if upload else []) if c.matched_case_id == digest.case_id), None
            )
            passage = self._passages.find(upload.text, citation.claimed.raw) if upload and citation else None
            if passage:
                context.append(SourcePassage("R1", passage))
        return context
