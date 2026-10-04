import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from caselens.application.ports.ai import AnswerRequest
from caselens.application.ports.digests import DigestRepository
from caselens.application.ports.repositories import CaseRepository, UnitOfWork, UploadRepository
from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion, decision_sources
from caselens.domain.case_digest import (
    CaseDigest,
    DigestField,
    DigestStatus,
    FieldKind,
    FieldOrigin,
    FieldState,
)
from caselens.domain.digest import GroundedAnswer, SourcePassage
from caselens.domain.errors import AiUnavailableError, CaseNotFoundError, DigestNotFoundError
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.reviewer_passage import ReviewerPassageFinder
from caselens.domain.services.ruling_locator import RulingLocator

logger = logging.getLogger(__name__)

_NO_ANSWERER = "Written explanations are not set up on this server."
_OVER_LIMIT = "The limit for written explanations today has been reached. Try again tomorrow."
_SERVICE_DOWN = "The explanation service did not answer. Try again in a moment."
_NOT_ENOUGH = "The decision does not say enough to answer this, so we left it empty."


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
    ) -> None:
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
            if f.kind is FieldKind.ANSWER and ((keys is None and f.state is FieldState.PENDING) or (keys is not None and f.key in keys))
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
        for item in waiting:
            refusal = self._refusal(item, sources)
            if refusal is not None:
                self._store(digest, refusal)
            else:
                asks.append(item)
        if not asks:
            return

        # The AI calls (each is a writer call, then a checker call) wait on the network and do not touch the database, so
        # they run side by side: two answers take as long as one. Saving stays in THIS thread (a database session is not
        # safe to share), and each answer is saved as soon as it is ready so the student sees it appear.
        with ThreadPoolExecutor(max_workers=min(len(asks), self._parallel)) as pool:
            futures = {pool.submit(self._ask, item, sources): item for item in asks}
            for future in as_completed(futures):
                item = futures[future]
                self._store(digest, self._field_from(item, future.result(), digest))

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
