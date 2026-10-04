import logging

from caselens.application.ports.repositories import UnitOfWork, UploadRepository
from caselens.application.use_cases.fetch_case_by_gr_number import FetchCaseByGrNumber
from caselens.application.use_cases.request_upload_digests import RequestUploadDigests
from caselens.domain.entities import UploadedCitation
from caselens.domain.errors import (
    CaseNotFoundError,
    CaseParseError,
    DomainError,
    SourceUnavailableError,
)
from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.domain.value_objects import MatchStatus


logger = logging.getLogger(__name__)


class ResolveUploadCitations:
    """Background step: fetch the official case for each pending citation and check it.

    One bad citation never stops the others. Progress is committed per citation so the
    student sees results appear while the rest are still being fetched.
    """

    def __init__(
        self,
        fetch_case: FetchCaseByGrNumber,
        matcher: CitationMatcher,
        uploads: UploadRepository,
        uow: UnitOfWork,
        auto_digests: "RequestUploadDigests | None" = None,
    ) -> None:
        self._fetch_case = fetch_case
        self._matcher = matcher
        self._uploads = uploads
        self._uow = uow
        self._auto_digests = auto_digests

    def execute(self, upload_id: int) -> None:
        upload = self._uploads.get(upload_id)
        if upload is None:
            raise DomainError(f"Upload {upload_id} does not exist.")

        for citation in upload.citations:
            if citation.status is MatchStatus.PENDING:
                self._resolve(citation)
                self._uploads.save(upload)
                self._uow.commit()

        still_pending = any(c.status is MatchStatus.PENDING for c in upload.citations)
        upload.status = "processing" if still_pending else "done"
        self._uploads.save(upload)
        self._uow.commit()
        if self._auto_digests:
            self._auto_digests.execute(upload_id)  # a digest for every case that was found

    def _resolve(self, citation: UploadedCitation) -> None:
        claimed = citation.claimed
        try:
            case = self._fetch_case.execute(claimed.gr_number, claimed.claimed_year)
        except CaseNotFoundError as exc:
            citation.record_failure(MatchStatus.NOT_FOUND, str(exc))
        except (SourceUnavailableError, CaseParseError) as exc:
            logger.warning("could not check G.R. No. %s: %s", claimed.gr_number, exc)
            citation.record_failure(MatchStatus.ERROR, str(exc))
        else:
            citation.record_match(self._matcher.match(claimed, case), case.id)
        logger.info("G.R. No. %s -> %s", claimed.gr_number, citation.status.value)
