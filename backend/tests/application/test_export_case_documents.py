"""Which cases go into the "all cases" file: found ones only, in the order cited, each once, within the limit."""
import pytest

from caselens.application.use_cases.export_case_documents import MAX_CASES_PER_FILE, ExportCaseDocument, ExportReviewCases
from caselens.domain.entities import Upload, UploadedCitation
from caselens.domain.errors import CaseNotFoundError, DomainError
from caselens.domain.value_objects import ClaimedCitation, GrNumber, MatchStatus
from tests.fakes import InMemoryCaseRepository, InMemoryUploadRepository
from tests.helpers import parse_official_case


class RecordingExporter:
    def __init__(self) -> None:
        self.exported: list[list[int]] = []

    def export(self, cases):
        self.exported.append([case.id for case in cases])
        return b"docx"


def citation(case_id: int | None, status: MatchStatus) -> UploadedCitation:
    item = UploadedCitation(ClaimedCitation(GrNumber("180046"), "GR no 180046"))
    item.status, item.matched_case_id = status, case_id
    return item


@pytest.fixture
def world():
    cases, uploads, exporter = InMemoryCaseRepository(), InMemoryUploadRepository(), RecordingExporter()
    for number in range(1, MAX_CASES_PER_FILE + 3):
        case = parse_official_case()
        case.source_url = f"{case.source_url}#{number}"
        cases.add(case)
    return cases, uploads, exporter


def test_found_cases_are_exported_in_the_order_cited_and_each_only_once(world):
    cases, uploads, exporter = world
    upload = uploads.add(Upload("My reviewer.docx", "x", [
        citation(3, MatchStatus.MATCH), citation(1, MatchStatus.MISMATCH), citation(3, MatchStatus.MATCH),
        citation(None, MatchStatus.NOT_FOUND), citation(None, MatchStatus.ERROR), citation(None, MatchStatus.PENDING),
        citation(2, MatchStatus.MATCH),
    ]))

    download = ExportReviewCases(uploads, cases, exporter).execute(upload.id)

    assert exporter.exported == [[3, 1, 2]]
    assert download.stem == "My-reviewer-all-cases"


def test_a_review_with_no_found_case_says_so_plainly(world):
    cases, uploads, exporter = world
    upload = uploads.add(Upload("r.pdf", "x", [citation(None, MatchStatus.NOT_FOUND)]))
    with pytest.raises(DomainError, match="nothing to download"):
        ExportReviewCases(uploads, cases, exporter).execute(upload.id)
    assert exporter.exported == []


def test_more_than_the_limit_is_refused_before_any_file_is_built(world):
    cases, uploads, exporter = world
    upload = uploads.add(Upload("big.docx", "x", [citation(n, MatchStatus.MATCH) for n in range(1, MAX_CASES_PER_FILE + 2)]))
    with pytest.raises(DomainError, match=f"at most {MAX_CASES_PER_FILE}"):
        ExportReviewCases(uploads, cases, exporter).execute(upload.id)
    assert exporter.exported == []


def test_exactly_the_limit_is_allowed(world):
    cases, uploads, exporter = world
    upload = uploads.add(Upload("ok.docx", "x", [citation(n, MatchStatus.MATCH) for n in range(1, MAX_CASES_PER_FILE + 1)]))
    ExportReviewCases(uploads, cases, exporter).execute(upload.id)
    assert len(exporter.exported[0]) == MAX_CASES_PER_FILE


def test_unknown_upload_or_case_is_not_found(world):
    cases, uploads, exporter = world
    with pytest.raises(CaseNotFoundError):
        ExportReviewCases(uploads, cases, exporter).execute(999)
    with pytest.raises(CaseNotFoundError):
        ExportCaseDocument(cases, exporter).execute(999)


def test_one_case_is_named_by_its_number(world):
    cases, _, exporter = world
    assert ExportCaseDocument(cases, exporter).execute(1).stem == "GR-180046-full-case"
