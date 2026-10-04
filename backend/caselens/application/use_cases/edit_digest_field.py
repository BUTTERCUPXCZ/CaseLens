from caselens.application.ports.digests import DigestRepository
from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.repositories import CaseRepository, UnitOfWork
from caselens.domain.case_digest import CaseDigest, DigestField, FieldKind, FieldOrigin, Passage
from caselens.domain.errors import CaseNotFoundError, DigestNotFoundError, InvalidDigestEditError
from caselens.domain.services.digest_field_factory import DigestFieldFactory
from caselens.domain.services.heading_sections import HeadingSections
from caselens.domain.services.ruling_locator import RulingLocator

_MAX_PICKED_PARAGRAPHS = 40
_MAX_TEXT_CHARS = 20000
_MAX_QUESTION_CHARS = 300


class EditDigestField:
    """What the student can do to a digest: type over a field, pick paragraphs of the decision, paste text,
    put the system's version back, or ask a question of their own.

    Picked paragraphs are always read from the stored decision (never typed in by the request), so
    "Picked by you" still means the Court's exact words. Pasted and typed text is marked as such.
    """

    def __init__(
        self,
        cases: CaseRepository,
        digests: DigestRepository,
        jobs: JobQueue,
        uow: UnitOfWork,
        sections: HeadingSections | None = None,
        rulings: RulingLocator | None = None,
    ) -> None:
        self._cases = cases
        self._digests = digests
        self._jobs = jobs
        self._uow = uow
        self._sections = sections or HeadingSections()
        self._rulings = rulings or RulingLocator()

    def write_text(self, digest_id: int, key: str, text: str) -> CaseDigest:
        digest, current = self._load(digest_id, key)
        self._check_length(text)
        return self._store(digest, current.edited_to(text, FieldOrigin.STUDENT_WRITTEN))

    def paste_text(self, digest_id: int, key: str, text: str) -> CaseDigest:
        digest, current = self._load(digest_id, key)
        self._verbatim_only(current)
        if not text.strip():
            raise InvalidDigestEditError("There is nothing to paste.")
        self._check_length(text)
        return self._store(digest, current.edited_to(text, FieldOrigin.STUDENT_PASTED))

    def pick_passage(self, digest_id: int, key: str, first: int, last: int) -> CaseDigest:
        digest, current = self._load(digest_id, key)
        self._verbatim_only(current)
        case = self._cases.get(digest.case_id)
        if case is None:
            raise CaseNotFoundError(f"Case {digest.case_id} does not exist.")
        paragraphs = case.full_text.split("\n")
        start = self._sections.body_start(paragraphs)
        ruling = self._rulings.locate(paragraphs)
        if start is None or ruling is None:
            raise InvalidDigestEditError("This decision's paragraphs could not be read, so a passage cannot be picked.")
        if first < start or last < first or last > ruling.last:
            raise InvalidDigestEditError(f"Pick paragraphs {start} to {ruling.last} of the decision.")
        if last - first + 1 > _MAX_PICKED_PARAGRAPHS:
            raise InvalidDigestEditError(f"Pick at most {_MAX_PICKED_PARAGRAPHS} paragraphs at a time.")
        # a picked run is shown whole (up to the limit above), not cut like the automatic sections are
        text = "\n\n".join(paragraphs[i] for i in range(first, last + 1))
        return self._store(digest, current.edited_to(text, FieldOrigin.STUDENT_PICKED, Passage(first, last)))

    def reset(self, digest_id: int, key: str) -> CaseDigest:
        digest, current = self._load(digest_id, key)
        return self._store(digest, current.reset())

    def ask(self, digest_id: int, question: str) -> CaseDigest:
        digest = self._digests.get(digest_id)
        if digest is None:
            raise DigestNotFoundError(f"Digest {digest_id} does not exist.")
        question = question.strip()
        if not question or len(question) > _MAX_QUESTION_CHARS:
            raise InvalidDigestEditError(f"Write a question of up to {_MAX_QUESTION_CHARS} characters.")
        taken = {f.key for f in digest.fields}
        number = next(n for n in range(1, 1000) if f"q{n}" not in taken)
        added = DigestFieldFactory.custom_question(f"q{number}", question)
        digest.fields.append(added)
        self._digests.save(digest)
        self._uow.commit()  # commit first so the worker sees the new field
        self._jobs.enqueue_build_digest(digest_id, [added.key])
        return digest

    def regenerate(self, digest_id: int, keys: list[str]) -> CaseDigest:
        digest = self._digests.get(digest_id)
        if digest is None:
            raise DigestNotFoundError(f"Digest {digest_id} does not exist.")
        for key in keys:
            current = digest.field_named(key)
            if current is None or current.kind is not FieldKind.ANSWER:
                raise InvalidDigestEditError(f"'{key}' is not a question this digest can answer.")
        self._jobs.enqueue_build_digest(digest_id, keys)
        return digest

    # -- helpers --------------------------------------------------------------

    def _load(self, digest_id: int, key: str) -> tuple[CaseDigest, DigestField]:
        digest = self._digests.get(digest_id)
        if digest is None:
            raise DigestNotFoundError(f"Digest {digest_id} does not exist.")
        current = digest.field_named(key)
        if current is None:
            raise InvalidDigestEditError(f"This digest has no field '{key}'.")
        return digest, current

    def _store(self, digest: CaseDigest, updated: DigestField) -> CaseDigest:
        digest.replace_field(updated)
        self._digests.save(digest)
        self._uow.commit()
        return digest

    @staticmethod
    def _verbatim_only(current: DigestField) -> None:
        if current.kind is not FieldKind.VERBATIM:
            raise InvalidDigestEditError(f"'{current.label}' is written from the decision; type over it instead.")

    @staticmethod
    def _check_length(text: str) -> None:
        if len(text) > _MAX_TEXT_CHARS:
            raise InvalidDigestEditError(f"That is too long (the limit is {_MAX_TEXT_CHARS} characters).")
