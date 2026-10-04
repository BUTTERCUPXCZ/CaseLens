from caselens.application.ports.repositories import UploadRepository
from caselens.application.use_cases.request_case_digest import RequestCaseDigest
from caselens.domain.value_objects import MatchStatus


class RequestUploadDigests:
    """After a reviewer is checked, start a digest for every case it cites that was found, so the student does
    not ask for them one by one. Safe to call again: a case that already has a digest in this review is left alone."""

    def __init__(self, uploads: UploadRepository, request_digest: RequestCaseDigest) -> None:
        self._uploads = uploads
        self._request = request_digest

    def execute(self, upload_id: int) -> int:
        upload = self._uploads.get(upload_id)
        if upload is None:
            return 0
        case_ids: list[int] = []
        for citation in upload.citations:
            if citation.status in (MatchStatus.MATCH, MatchStatus.MISMATCH) and citation.matched_case_id not in case_ids:
                case_ids.append(citation.matched_case_id)
        for case_id in case_ids:
            self._request.execute(case_id, upload_id)
        return len(case_ids)
