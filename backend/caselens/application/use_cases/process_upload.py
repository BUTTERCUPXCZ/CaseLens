from caselens.application.ports.gateways import JobQueue, UploadedFileReader
from caselens.application.ports.repositories import CaseRepository, UnitOfWork, UploadRepository
from caselens.application.use_cases.fetch_case_by_gr_number import FetchCaseByGrNumber
from caselens.application.use_cases.request_upload_digests import RequestUploadDigests
from caselens.domain.entities import Upload, UploadedCitation
from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.domain.value_objects import MatchStatus


class ProcessUpload:
    """Reads an uploaded reviewer and checks every cited G.R. number.

    Citations whose case is already stored are checked immediately. The rest are left
    `pending` and handed to the background worker, because fetching from Lawphil is slow.
    """

    def __init__(
        self,
        reader: UploadedFileReader,
        extractor: GrCitationExtractor,
        matcher: CitationMatcher,
        known_cases: FetchCaseByGrNumber,
        uploads: UploadRepository,
        jobs: JobQueue,
        uow: UnitOfWork,
        auto_digests: "RequestUploadDigests | None" = None,
    ) -> None:
        self._reader = reader
        self._extractor = extractor
        self._matcher = matcher
        self._known_cases = known_cases
        self._uploads = uploads
        self._jobs = jobs
        self._uow = uow
        self._auto_digests = auto_digests

    def execute(self, filename: str, data: bytes) -> Upload:
        text = self._reader.read(filename, data)
        citations = [UploadedCitation(claimed) for claimed in self._extractor.extract(text)]
        upload = Upload(filename=filename, text=text, file_data=data, citations=citations)

        for citation in citations:
            case = self._known_cases.find_stored(citation.claimed.gr_number)
            if case:
                citation.record_match(self._matcher.match(citation.claimed, case), case.id)

        has_pending = any(c.status is MatchStatus.PENDING for c in citations)
        upload.status = "processing" if has_pending else "done"

        self._uploads.add(upload)
        self._uow.commit()  # commit first so the worker can see the upload
        if has_pending:
            self._jobs.enqueue_resolve_upload(upload.id)
        if self._auto_digests:
            self._auto_digests.execute(upload.id)  # the cases already stored get their digests now; the rest when the worker finds them
        return upload
