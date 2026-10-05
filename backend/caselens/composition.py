"""Composition root: the only module that knows which concrete class implements which port.

Everything else depends on abstractions. Tests (and a future E-Library source) swap
implementations here without touching a use case.
"""
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from caselens.application.ports.catalog import IndexFetcher, YearDiscovery
from caselens.application.ports.gateways import CaseFetcher, CaseLocator, JobQueue
from caselens.application.ports.ai import AnswerChecker, AnswerWriter
from caselens.application.use_cases.answer_case_question import AnswerCaseQuestion
from caselens.application.use_cases.attach_case_to_citation import AttachCaseToCitation
from caselens.application.use_cases.build_case_digest import BuildCaseDigest
from caselens.application.use_cases.build_finished_reviewer import BuildFinishedReviewer
from caselens.application.use_cases.request_upload_digests import RequestUploadDigests
from caselens.application.use_cases.delete_upload import DeleteUpload
from caselens.application.use_cases.export_case_documents import ExportCaseDocument, ExportReviewCases
from caselens.application.use_cases.edit_digest_field import EditDigestField
from caselens.application.use_cases.get_digest import GetDigest
from caselens.application.use_cases.request_case_digest import RequestCaseDigest
from caselens.application.use_cases.build_catalog import BuildCatalog
from caselens.application.use_cases.fetch_case_by_gr_number import FetchCaseByGrNumber
from caselens.application.use_cases.get_case import GetCase
from caselens.application.use_cases.get_case_insights import GetCaseInsights
from caselens.application.use_cases.get_catalog_status import GetCatalogStatus
from caselens.application.use_cases.keep_catalog_fresh import KeepCatalogFresh
from caselens.application.use_cases.search_catalog import SearchCatalog
from caselens.application.use_cases.start_catalog_build import StartCatalogBuild
from caselens.application.use_cases.get_trends import GetTrends
from caselens.application.use_cases.get_upload import GetUpload
from caselens.application.use_cases.ingest_case import IngestCase
from caselens.application.use_cases.list_cases import ListCases
from caselens.application.use_cases.list_uploads import ListUploads
from caselens.application.use_cases.process_upload import ProcessUpload
from caselens.application.use_cases.resolve_upload_citations import ResolveUploadCitations
from caselens.application.use_cases.refetch_damaged_cases import RefetchDamagedCases
from caselens.application.use_cases.reparse_stored_cases import ReparseStoredCases
from caselens.application.use_cases.retry_upload import RetryUpload
from caselens.application.use_cases.search_case import SearchCaseByGrNumber
from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.domain.services.insight_builder import CaseInsightBuilder
from caselens.infrastructure.config import Settings, get_settings
from caselens.infrastructure.db.catalog_repository import SqlCatalogRepository
from caselens.infrastructure.db.digest_repository import SqlDigestRepository
from caselens.infrastructure.db.insight_queries import SqlInsightQueries
from caselens.infrastructure.db.repositories import (
    SqlCaseRepository,
    SqlMonthIndexRepository,
    SqlUnitOfWork,
    SqlUploadRepository,
)
from caselens.infrastructure.ai.gemini_answerer import (
    PROMPT_VERSION,
    GeminiAnswerChecker,
    GeminiAnswerWriter,
    _GeminiCall,
)
from caselens.infrastructure.docx_case_export import DocxCaseExporter
from caselens.infrastructure.docx_export import DocxDigestExporter
from caselens.infrastructure.extraction.block_reader import CompositeBlockReader, DocxBlockReader, PdfBlockReader
from caselens.infrastructure.extraction.composite_extractor import CompositeDocumentExtractor
from caselens.infrastructure.extraction.docx_extractor import DocxTextExtractor
from caselens.infrastructure.extraction.pdf_extractor import PdfTextExtractor
from caselens.infrastructure.lawphil.case_source import LawphilCaseSource
from caselens.infrastructure.lawphil.catalog_parser import LawphilCatalogParser
from caselens.infrastructure.lawphil.catalog_source import LawphilIndexFetcher, LawphilYearDiscovery
from caselens.infrastructure.lawphil.html_parser import PARSER_VERSION, LawphilCaseParser
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient
from caselens.infrastructure.lawphil.url_scheme import LawphilUrlScheme
from caselens.infrastructure.db.job_lock_repository import SqlJobLockRepository
from caselens.infrastructure.db.session import engine
from caselens.infrastructure.queue import lock_keys
from caselens.infrastructure.queue.rabbit_job_queue import RabbitJobQueue


@lru_cache
def _lawphil_pages() -> ThrottledPageClient:
    """One client per process, so the 1 request/second limit holds across all jobs."""
    return ThrottledPageClient.from_settings(get_settings())


@lru_cache
def _job_queue() -> JobQueue:
    locks = SqlJobLockRepository(engine)
    if get_settings().queue_backend == "threads":
        from caselens.infrastructure.queue.thread_job_queue import ThreadJobQueue  # imported here: it needs Services

        return ThreadJobQueue(locks)  # jobs run inside this process: no RabbitMQ and no workers
    from caselens.infrastructure.queue import actors  # imported here: it connects the broker

    return RabbitJobQueue(locks, actors)


def start_background_jobs() -> None:
    """Called once when the API starts. With the thread queue, work that was running at the last stop is queued again."""
    if get_settings().queue_backend == "threads":
        from caselens.infrastructure.queue.recovery import requeue_unfinished_work

        requeue_unfinished_work(_job_queue(), SqlJobLockRepository(engine))


class Services:
    """Builds use cases for one unit of work (one HTTP request or one background job)."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        case_locator: CaseLocator | None = None,
        case_fetcher: CaseFetcher | None = None,
        jobs: JobQueue | None = None,
        year_discovery: YearDiscovery | None = None,
        index_fetcher: IndexFetcher | None = None,
        build_probe: Callable[[], bool] | None = None,
        answer_writer: AnswerWriter | None = None,
        answer_checker: AnswerChecker | None = None,
        ai_enabled: bool | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._session = session
        self._case_locator = case_locator
        self._case_fetcher = case_fetcher
        self._jobs = jobs
        self._year_discovery = year_discovery
        self._index_fetcher = index_fetcher
        self._build_probe = build_probe
        self._answer_writer = answer_writer
        self._answer_checker = answer_checker
        self._ai_enabled = ai_enabled

        self._cases = SqlCaseRepository(session)
        self._uploads = SqlUploadRepository(session)
        self._digests = SqlDigestRepository(session)
        self._uow = SqlUnitOfWork(session)
        self._matcher = CitationMatcher()

    # -- adapters chosen lazily so tests can inject fakes and never touch the network --

    def _lawphil(self) -> LawphilCaseSource:
        return LawphilCaseSource(
            _lawphil_pages(),
            SqlMonthIndexRepository(self._session),
            LawphilUrlScheme(self._settings.lawphil_base_url),
            catalog=SqlCatalogRepository(self._session),
        )

    def _locator(self) -> CaseLocator:
        return self._case_locator or self._lawphil()

    def _fetcher(self) -> CaseFetcher:
        return self._case_fetcher or self._lawphil()

    def _job_queue(self) -> JobQueue:
        return self._jobs or _job_queue()

    def _discovery(self) -> YearDiscovery:
        return self._year_discovery or LawphilYearDiscovery(
            _lawphil_pages(),
            LawphilUrlScheme(self._settings.lawphil_base_url),
            self._settings.lawphil_base_url,
        )

    def _index_source(self) -> IndexFetcher:
        return self._index_fetcher or LawphilIndexFetcher(_lawphil_pages())

    def _catalog_building(self) -> bool:
        probe = self._build_probe or (lambda: SqlJobLockRepository(engine).is_held(lock_keys.CATALOG_BUILD_KEY))
        try:
            return probe()
        except (OSError, SQLAlchemyError):  # a lock table that cannot be read must not break the status page
            return False

    # -- use cases -----------------------------------------------------------------

    def ingest_case(self) -> IngestCase:
        return IngestCase(self._fetcher(), LawphilCaseParser(), self._cases, self._uow)

    def fetch_case_by_gr_number(self) -> FetchCaseByGrNumber:
        return FetchCaseByGrNumber(self._locator(), self.ingest_case(), self._cases)

    def process_upload(self) -> ProcessUpload:
        reader = CompositeDocumentExtractor([PdfTextExtractor(), DocxTextExtractor()])
        return ProcessUpload(
            reader,
            GrCitationExtractor(),
            self._matcher,
            self.fetch_case_by_gr_number(),
            self._uploads,
            self._job_queue(),
            self._uow,
            self._auto_digests(),
        )

    def resolve_upload_citations(self) -> ResolveUploadCitations:
        return ResolveUploadCitations(
            self.fetch_case_by_gr_number(), self._matcher, self._uploads, self._uow, self._auto_digests()
        )

    def search_case(self) -> SearchCaseByGrNumber:
        return SearchCaseByGrNumber(self._cases, self._job_queue(), SqlCatalogRepository(self._session))

    def get_case(self) -> GetCase:
        return GetCase(self._cases)

    def get_upload(self) -> GetUpload:
        return GetUpload(self._uploads, self._cases)

    def delete_upload(self) -> DeleteUpload:
        return DeleteUpload(self._uploads, self._uow)

    def list_uploads(self) -> ListUploads:
        return ListUploads(self._uploads)

    def list_cases(self) -> ListCases:
        return ListCases(self._cases)

    def retry_upload(self) -> RetryUpload:
        return RetryUpload(self._uploads, self._job_queue(), self._uow)

    def attach_case_to_citation(self) -> AttachCaseToCitation:
        return AttachCaseToCitation(self.ingest_case(), self._matcher, self._uploads, self._uow, self._auto_digests())

    def refetch_damaged_cases(self) -> RefetchDamagedCases:
        return RefetchDamagedCases(self._cases, self._fetcher(), LawphilCaseParser(), self._uow)

    def build_catalog(self) -> BuildCatalog:
        return BuildCatalog(
            self._discovery(), self._index_source(), LawphilCatalogParser(), SqlCatalogRepository(self._session)
        )

    def search_catalog(self) -> SearchCatalog:
        return SearchCatalog(SqlCatalogRepository(self._session))

    def catalog_status(self) -> GetCatalogStatus:
        return GetCatalogStatus(SqlCatalogRepository(self._session), self._catalog_building)

    def start_catalog_build(self) -> StartCatalogBuild:
        return StartCatalogBuild(self._job_queue(), self._settings.catalog_first_year)

    def keep_catalog_fresh(self) -> KeepCatalogFresh:
        return KeepCatalogFresh(
            SqlCatalogRepository(self._session), self._job_queue(), self._settings.catalog_first_year
        )

    def reparse_stored_cases(self) -> ReparseStoredCases:
        return ReparseStoredCases(self._cases, LawphilCaseParser(), PARSER_VERSION, self._uow)

    def get_case_insights(self) -> GetCaseInsights:
        return GetCaseInsights(self._cases, CaseInsightBuilder())

    def get_trends(self) -> GetTrends:
        return GetTrends(SqlInsightQueries(self._session))

    # -- case digests ----------------------------------------------------------------

    def _answerer(self) -> AnswerCaseQuestion | None:
        """The AI that writes digest answers, or None when no key is set (the digest then works without it)."""
        if self._answer_writer is not None and self._answer_checker is not None:
            return AnswerCaseQuestion(self._answer_writer, self._answer_checker)
        enabled = self._ai_enabled if self._ai_enabled is not None else bool(self._settings.gemini_api_key)
        if not enabled:
            return None
        call = _GeminiCall(self._settings)
        return AnswerCaseQuestion(
            GeminiAnswerWriter(self._settings, call), GeminiAnswerChecker(self._settings, call)
        )

    def _ai_budget_left(self) -> bool:
        midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return self._digests.count_ai_since(midnight) < self._settings.digest_ai_daily_limit

    def request_case_digest(self) -> RequestCaseDigest:
        return RequestCaseDigest(self._cases, self._digests, self._job_queue(), self._uow)

    def build_case_digest(self) -> BuildCaseDigest:
        return BuildCaseDigest(
            self._cases,
            self._digests,
            self._uploads,
            self._uow,
            self._answerer(),
            model=self._settings.gemini_writer_model,
            prompt_version=PROMPT_VERSION,
            ai_allowed=self._ai_budget_left,
            parallel=self._settings.digest_parallel_answers,
        )

    def edit_digest_field(self) -> EditDigestField:
        return EditDigestField(self._cases, self._digests, self._job_queue(), self._uow)

    def get_digest(self) -> GetDigest:
        return GetDigest(self._digests)

    def _auto_digests(self) -> RequestUploadDigests | None:
        if not self._settings.auto_digest_on_upload:
            return None
        return RequestUploadDigests(self._uploads, self.request_case_digest())

    def build_finished_reviewer(self) -> BuildFinishedReviewer:
        reader = CompositeBlockReader([PdfBlockReader(), DocxBlockReader()])
        return BuildFinishedReviewer(self._uploads, self._digests, self._cases, reader)

    def export_case_document(self) -> ExportCaseDocument:
        return ExportCaseDocument(self._cases, DocxCaseExporter())

    def export_review_cases(self) -> ExportReviewCases:
        return ExportReviewCases(self._uploads, self._cases, DocxCaseExporter())

    def reviewer_exporter(self) -> DocxDigestExporter:
        return DocxDigestExporter()

    def original_upload(self, upload_id: int) -> bytes | None:
        """The file the student uploaded, kept so the finished reviewer can be built from it."""
        return self._uploads.get_file_data(upload_id)
