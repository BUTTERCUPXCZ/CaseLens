import re
from dataclasses import dataclass

from caselens.application.ports.gateways import CaseDocumentExporter
from caselens.application.ports.repositories import CaseRepository, UploadRepository
from caselens.domain.errors import CaseNotFoundError, DomainError
from caselens.domain.value_objects import MatchStatus

MAX_CASES_PER_FILE = 40  # one Word file is built in memory; a free server has little of it


@dataclass(frozen=True)
class CaseDownload:
    data: bytes
    stem: str  # a file name without its extension, safe to use as one


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")


class ExportCaseDocument:
    """One decision, in full, as a Word file: for a student who wants to write the digest by hand."""

    def __init__(self, cases: CaseRepository, exporter: CaseDocumentExporter) -> None:
        self._cases = cases
        self._exporter = exporter

    def execute(self, case_id: int) -> CaseDownload:
        case = self._cases.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"Case {case_id} does not exist.")
        return CaseDownload(self._exporter.export([case]), f"GR-{_safe(case.gr_no.value)}-full-case")


class ExportReviewCases:
    """Every case a reviewer cites that was found, in the order they are cited, as one Word file."""

    def __init__(self, uploads: UploadRepository, cases: CaseRepository, exporter: CaseDocumentExporter) -> None:
        self._uploads = uploads
        self._cases = cases
        self._exporter = exporter

    def execute(self, upload_id: int) -> CaseDownload:
        upload = self._uploads.get(upload_id)
        if upload is None:
            raise CaseNotFoundError(f"Upload {upload_id} does not exist.")
        case_ids: list[int] = []
        for citation in upload.citations:
            found = citation.status in (MatchStatus.MATCH, MatchStatus.MISMATCH)
            if found and citation.matched_case_id is not None and citation.matched_case_id not in case_ids:
                case_ids.append(citation.matched_case_id)  # a decision cited twice is downloaded once
        if not case_ids:
            raise DomainError("This review has no case we found yet, so there is nothing to download.")
        if len(case_ids) > MAX_CASES_PER_FILE:
            raise DomainError(f"This review cites {len(case_ids)} cases. A download can have at most {MAX_CASES_PER_FILE}.")
        cases = [case for case_id in case_ids if (case := self._cases.get(case_id)) is not None]
        stem = _safe(upload.filename.rsplit(".", 1)[0]) or "reviewer"
        return CaseDownload(self._exporter.export(cases), f"{stem}-all-cases")
