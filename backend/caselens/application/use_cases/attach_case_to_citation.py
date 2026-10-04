from caselens.application.ports.repositories import UnitOfWork, UploadRepository
from caselens.application.use_cases.ingest_case import IngestCase
from caselens.application.use_cases.request_upload_digests import RequestUploadDigests
from caselens.domain.errors import CaseNotFoundError
from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.domain.value_objects import MatchStatus


class AttachCaseToCitation:
    """The student pastes the Lawphil link for a citation we could not find.

    The page is fetched and stored like any other, then checked against what the student
    wrote. If it turns out to be a different case than the citation names, the check says
    so (G.R. number mismatch) instead of silently accepting it.
    """

    def __init__(
        self,
        ingest: IngestCase,
        matcher: CitationMatcher,
        uploads: UploadRepository,
        uow: UnitOfWork,
        auto_digests: "RequestUploadDigests | None" = None,
    ) -> None:
        self._ingest = ingest
        self._matcher = matcher
        self._uploads = uploads
        self._uow = uow
        self._auto_digests = auto_digests

    def execute(self, upload_id: int, citation_id: int, url: str) -> None:
        upload = self._uploads.get(upload_id)
        if upload is None:
            raise CaseNotFoundError(f"Upload {upload_id} does not exist.")
        citation = next((c for c in upload.citations if c.id == citation_id), None)
        if citation is None:
            raise CaseNotFoundError(f"Citation {citation_id} is not part of upload {upload_id}.")

        case = self._ingest.execute(url)  # raises InvalidSourceUrlError for non-Lawphil links
        citation.record_match(self._matcher.match(citation.claimed, case), case.id)

        still_pending = any(c.status is MatchStatus.PENDING for c in upload.citations)
        upload.status = "processing" if still_pending else "done"
        self._uploads.save(upload)
        self._uow.commit()
        if self._auto_digests:
            self._auto_digests.execute(upload_id)
