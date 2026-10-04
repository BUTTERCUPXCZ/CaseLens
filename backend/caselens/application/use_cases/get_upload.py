from dataclasses import dataclass

from caselens.application.ports.repositories import CaseRepository, UploadRepository
from caselens.domain.entities import CaseSummary, Upload
from caselens.domain.errors import CaseNotFoundError


@dataclass(frozen=True)
class UploadReport:
    upload: Upload
    cases: dict[int, CaseSummary]  # matched case id -> its official record (name, date, link, ...)


class GetUpload:
    def __init__(self, uploads: UploadRepository, cases: CaseRepository) -> None:
        self._uploads = uploads
        self._cases = cases

    def execute(self, upload_id: int) -> UploadReport:
        upload = self._uploads.get(upload_id)
        if upload is None:
            raise CaseNotFoundError(f"Upload {upload_id} does not exist.")
        matched = sorted({c.matched_case_id for c in upload.citations if c.matched_case_id})
        return UploadReport(upload, self._cases.summaries(matched))
