from caselens.application.ports.digests import DigestRepository
from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.repositories import CaseRepository, UnitOfWork
from caselens.domain.case_digest import CaseDigest, DigestStatus, DigestTemplate, FieldState
from caselens.domain.errors import CaseNotFoundError
from caselens.domain.services.digest_field_factory import DigestFieldFactory


class RequestCaseDigest:
    """Starts a digest for one cited case. The Court's own text (Facts, Issue, Ruling) is filled in at once, so the
    student sees it immediately; the AI answers are queued and appear one by one.

    Asking again for the same case in the same review returns the digest that already exists (and never queues the
    AI work a second time), unless an earlier attempt failed.
    """

    def __init__(
        self,
        cases: CaseRepository,
        digests: DigestRepository,
        jobs: JobQueue,
        uow: UnitOfWork,
        factory: DigestFieldFactory | None = None,
    ) -> None:
        self._cases = cases
        self._digests = digests
        self._jobs = jobs
        self._uow = uow
        self._factory = factory or DigestFieldFactory()

    def execute(
        self,
        case_id: int,
        upload_id: int | None = None,
        template: DigestTemplate = DigestTemplate.FULL,
        questions: list[str] | None = None,
    ) -> CaseDigest:
        case = self._cases.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")

        existing = self._digests.find(case_id, upload_id)
        if existing is not None:
            if existing.status is DigestStatus.FAILED:
                existing.status, existing.error = DigestStatus.PENDING, None
                self._digests.save(existing)
                self._uow.commit()
                self._jobs.enqueue_build_digest(existing.id)
            return existing

        digest = CaseDigest(
            case_id=case_id,
            upload_id=upload_id,
            template=template,
            fields=self._factory.build(template, case.full_text, [q.strip() for q in (questions or []) if q.strip()]),
            parser_version=case.parser_version,
        )
        waiting = any(f.state is FieldState.PENDING for f in digest.fields)  # an answer to write, or a passage to look for
        digest.status = DigestStatus.PENDING if waiting else DigestStatus.READY
        digest = self._digests.add(digest)
        self._uow.commit()  # commit first so the worker can see it
        if waiting:
            self._jobs.enqueue_build_digest(digest.id)
        return digest
