"""A tiny composition root for tests: in-memory fakes wired to the real use cases."""
from caselens.application.use_cases.attach_case_to_citation import AttachCaseToCitation
from caselens.application.use_cases.fetch_case_by_gr_number import FetchCaseByGrNumber
from caselens.application.use_cases.ingest_case import IngestCase
from caselens.application.use_cases.list_cases import ListCases
from caselens.application.use_cases.list_uploads import ListUploads
from caselens.application.use_cases.process_upload import ProcessUpload
from caselens.application.use_cases.resolve_upload_citations import ResolveUploadCitations
from caselens.application.use_cases.retry_upload import RetryUpload
from caselens.application.use_cases.search_case import SearchCaseByGrNumber
from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.infrastructure.extraction.composite_extractor import CompositeDocumentExtractor
from caselens.infrastructure.extraction.docx_extractor import DocxTextExtractor
from caselens.infrastructure.extraction.pdf_extractor import PdfTextExtractor
from caselens.infrastructure.lawphil.html_parser import LawphilCaseParser
from tests.fakes import (
    FakeJobQueue,
    FakeUnitOfWork,
    FixtureCaseSource,
    InMemoryCaseRepository,
    InMemoryUploadRepository,
)
from tests.helpers import OFFICIAL_URL, official_html


class World:
    """All the fakes plus the use cases wired to them."""

    def __init__(self) -> None:
        self.cases = InMemoryCaseRepository()
        self.uploads = InMemoryUploadRepository()
        self.uow = FakeUnitOfWork()
        self.jobs = FakeJobQueue()
        self.source = FixtureCaseSource({OFFICIAL_URL: official_html()}, {"180046": [OFFICIAL_URL]})
        self.matcher = CitationMatcher()

        self.ingest = IngestCase(self.source, LawphilCaseParser(), self.cases, self.uow)
        self.fetch_case = FetchCaseByGrNumber(self.source, self.ingest, self.cases)
        self.process = ProcessUpload(
            CompositeDocumentExtractor([PdfTextExtractor(), DocxTextExtractor()]),
            GrCitationExtractor(),
            self.matcher,
            self.fetch_case,
            self.uploads,
            self.jobs,
            self.uow,
        )
        self.resolve = ResolveUploadCitations(self.fetch_case, self.matcher, self.uploads, self.uow)
        self.search = SearchCaseByGrNumber(self.cases, self.jobs)
        self.list_uploads = ListUploads(self.uploads)
        self.list_cases = ListCases(self.cases)
        self.retry = RetryUpload(self.uploads, self.jobs, self.uow)
        self.attach = AttachCaseToCitation(self.ingest, self.matcher, self.uploads, self.uow)
