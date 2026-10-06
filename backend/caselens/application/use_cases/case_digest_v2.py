import logging
from collections.abc import Callable
from datetime import UTC, datetime

from caselens.application.ports.digests import CaseDigestRepository
from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.repositories import CaseRepository, UnitOfWork
from caselens.application.use_cases.build_digest_request import OpinionText, build_digest_request
from caselens.application.use_cases.write_case_digest import WriteCaseDigest
from caselens.domain.digest_v2 import CaseDigestV2, DigestState, clean_scope, scope_key
from caselens.domain.entities import Case
from caselens.domain.errors import AiCreditError, AiUnavailableError, CaseNotFoundError, DigestNotFoundError

logger = logging.getLogger(__name__)


def _reason(exc: AiUnavailableError) -> str:
    """What the student reads: a credit problem says so (asking again cannot help); anything else is a passing outage."""
    return AiCreditError.STUDENT_MESSAGE if isinstance(exc, AiCreditError) else _SERVICE_DOWN

_NO_WRITER = "Written digests are not set up on this server."
OVER_LIMIT_MESSAGE = "The limit for case digests this month has been reached. It will continue when the limit resets, or when it is raised."
_SERVICE_DOWN = "The writing service did not answer. Try again in a moment."


def opinions_of(case: Case) -> list[OpinionText]:
    """The separate opinions printed with the decision (the parser reads them from newer and older pages alike)."""
    return [OpinionText(o.author or "", o.kind.replace("_", " "), [line for line in o.text.split("\n") if line.strip()]) for o in case.opinions]


def month_start(now: datetime) -> datetime:
    return now.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class RequestCaseDigestV2:
    """Asks for the case digest of a case, for a topic scope ("" = the standard digest). It is written once, in the background, and kept;
    asking again with the same scope returns the same digest. A related page (a Resolution, a repeat) is digested under its main case."""

    def __init__(self, cases: CaseRepository, digests: CaseDigestRepository, jobs: JobQueue, uow: UnitOfWork) -> None:
        self._cases = cases
        self._digests = digests
        self._jobs = jobs
        self._uow = uow

    def execute(self, case_id: int, scope: str = "", regenerate: bool = False) -> CaseDigestV2:
        found = self._cases.summaries([case_id]).get(case_id)
        if found is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")
        main_id = found.main_case_id or case_id
        existing = self._digests.get(main_id, scope_key(scope))
        if existing is not None and not regenerate and existing.state in (DigestState.READY, DigestState.PENDING):
            return existing
        digest = existing or CaseDigestV2(case_id=main_id, scope=clean_scope(scope))
        digest.state, digest.error = DigestState.PENDING, None  # an older draft stays visible until the new one is ready
        saved = self._digests.save(digest)
        self._uow.commit()  # commit first so the worker can see it
        assert saved.id is not None
        self._jobs.enqueue_case_digest(saved.id)
        return saved


class GetCaseDigestV2:
    def __init__(self, cases: CaseRepository, digests: CaseDigestRepository) -> None:
        self._cases = cases
        self._digests = digests

    def execute(self, case_id: int, scope: str = "") -> tuple[Case, CaseDigestV2 | None]:
        case = self._cases.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")
        return case, self._digests.get(case.main_case_id or case_id, scope_key(scope))


class BuildCaseDigestV2:
    """The background job: write the digest (focused on its scope, if it has one), check every sentence, save it.

    A failure leaves a plain reason on the digest (never a half-written one passed off as finished); asking again retries."""

    def __init__(
        self,
        cases: CaseRepository,
        digests: CaseDigestRepository,
        uow: UnitOfWork,
        writer: WriteCaseDigest | None,
        *,
        model: str = "",
        prompt_version: str = "",
        monthly_limit: int = 0,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        usage: Callable[[], tuple[int, int]] = lambda: (0, 0),
    ) -> None:
        self._cases = cases
        self._digests = digests
        self._uow = uow
        self._writer = writer
        self._model = model
        self._prompt_version = prompt_version
        self._monthly_limit = monthly_limit
        self._clock = clock
        self._usage = usage

    def execute(self, digest_id: int) -> CaseDigestV2:
        digest = self._digests.get_by_id(digest_id)
        if digest is None:
            raise DigestNotFoundError(f"Case digest {digest_id} does not exist.")
        case = self._cases.get(digest.case_id)
        if case is None:
            raise CaseNotFoundError(f"Case {digest.case_id} does not exist.")
        if digest.state is DigestState.READY:
            return digest  # a job runs for a PENDING digest; a repeated message finds it already done
        if self._writer is None:
            return self._finish(digest, DigestState.FAILED, _NO_WRITER)
        if self._monthly_limit and self._digests.count_started_since(month_start(self._clock())) > self._monthly_limit:
            return self._finish(digest, DigestState.FAILED, OVER_LIMIT_MESSAGE)

        tags = ", ".join(s.name for s in case.subjects) or None
        request = build_digest_request(case, opinions_of(case), tags, digest.scope)
        self._uow.commit()  # end the read before the AI call (minutes): SQLite refuses a late save from a read held that long
        before = self._usage()
        try:
            result = self._writer.execute(request)
        except AiUnavailableError as exc:
            logger.warning("case %s digest %s: not written: %s", case.id, digest_id, exc)
            return self._finish(digest, DigestState.FAILED, _reason(exc))
        after = self._usage()
        digest.draft, digest.written, digest.dropped = result.draft, result.written, len(result.dropped)
        digest.model, digest.prompt_version = self._model, self._prompt_version
        digest.input_tokens, digest.output_tokens = after[0] - before[0], after[1] - before[1]
        for line in result.dropped:
            logger.info("case %s digest %s: dropped %s (%s)", case.id, digest_id, line.section.value, line.reason[:100])
        return self._finish(digest, DigestState.READY, None)

    def _finish(self, digest: CaseDigestV2, state: DigestState, error: str | None) -> CaseDigestV2:
        digest.state, digest.error = state, error
        saved = self._digests.save(digest)
        self._uow.commit()
        return saved
