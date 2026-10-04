"""Use cases run against in-memory fakes: no database, no network, no HTTP."""
import pytest

from caselens.application.use_cases.search_case import SearchStatus
from caselens.domain.entities import Upload, UploadedCitation
from caselens.domain.errors import DocumentExtractionError, UnsupportedDocumentError
from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.domain.value_objects import GrNumber, MatchStatus
from tests.helpers import OFFICIAL_URL, parse_official_case, sample_pdf_bytes
from tests.world import World

GR = GrNumber("180046")


@pytest.fixture
def world() -> World:
    return World()


# -- IngestCase ---------------------------------------------------------------------


def test_ingest_downloads_parses_and_stores_once(world):
    first = world.ingest.execute(OFFICIAL_URL)
    second = world.ingest.execute(OFFICIAL_URL)

    assert first.id == second.id
    assert world.source.fetch_calls == [OFFICIAL_URL]  # second call came from storage
    assert len(world.cases.cases) == 1


def test_ingest_survives_a_race_where_another_worker_stored_it_first(world):
    stored = parse_official_case()
    world.cases.add(stored)
    world.cases.fail_with_duplicate_once = True
    # get_by_source_url must miss once, then find it: simulate by clearing then restoring
    original = world.cases.get_by_source_url
    calls = []

    def flaky_lookup(url):
        calls.append(url)
        return None if len(calls) == 1 else original(url)

    world.cases.get_by_source_url = flaky_lookup
    assert world.ingest.execute(OFFICIAL_URL).id == stored.id


# -- ProcessUpload ------------------------------------------------------------------


def test_upload_of_unknown_case_is_pending_and_queued(world):
    upload = world.process.execute("sample case.pdf", sample_pdf_bytes())

    assert upload.status == "processing"
    (citation,) = upload.citations
    assert citation.status is MatchStatus.PENDING
    assert str(citation.claimed.gr_number) == "180046"
    assert world.jobs.resolve_upload_ids == [upload.id]
    assert world.uow.commits == 1  # committed before the job was queued


def test_upload_of_stored_case_is_checked_immediately_without_a_job(world):
    world.cases.add(parse_official_case())

    upload = world.process.execute("sample case.pdf", sample_pdf_bytes())

    assert upload.status == "done"
    (citation,) = upload.citations
    assert citation.status is MatchStatus.MISMATCH
    assert citation.mismatches == {"year": {"claimed": 2010, "official": 2009}}
    assert citation.matched_case_id == 1
    assert world.jobs.resolve_upload_ids == []
    assert world.source.fetch_calls == []


def test_unsupported_and_corrupt_files_store_nothing(world):
    with pytest.raises(UnsupportedDocumentError):
        world.process.execute("notes.txt", b"hello")
    with pytest.raises(DocumentExtractionError):
        world.process.execute("broken.pdf", b"not a pdf")
    assert world.uploads.uploads == {}


# -- ResolveUploadCitations ---------------------------------------------------------


def test_worker_fetches_the_case_and_finishes_the_upload(world):
    upload = world.process.execute("sample case.pdf", sample_pdf_bytes())

    world.resolve.execute(upload.id)

    (citation,) = world.uploads.get(upload.id).citations
    assert citation.status is MatchStatus.MISMATCH
    assert citation.mismatches["year"] == {"claimed": 2010, "official": 2009}
    assert world.uploads.get(upload.id).status == "done"
    assert world.source.locate_calls == [("180046", 2010)]  # used the (wrong) claimed year as a hint


def test_unknown_number_becomes_not_found_never_a_guess(world):
    world.source.locations = {}
    upload = world.process.execute("sample case.pdf", sample_pdf_bytes())

    world.resolve.execute(upload.id)

    (citation,) = world.uploads.get(upload.id).citations
    assert citation.status is MatchStatus.NOT_FOUND
    assert "not found on Lawphil" in citation.message
    assert citation.matched_case_id is None


def new_upload(world: World, text: str) -> Upload:
    claims = GrCitationExtractor().extract(text)
    return world.uploads.add(Upload("x.pdf", text, [UploadedCitation(c) for c in claims]))


def test_source_outage_marks_error_and_other_citations_still_finish(world):
    upload = new_upload(
        world,
        "Review Center v Ermita, GR no 180046 (April 2, 2009)\nOther v. Case, GR no 123456 (2001)",
    )
    world.source.down_for = {"123456"}

    world.resolve.execute(upload.id)

    by_gr = {str(c.claimed.gr_number): c for c in world.uploads.get(upload.id).citations}
    assert by_gr["180046"].status is MatchStatus.MATCH
    assert by_gr["123456"].status is MatchStatus.ERROR
    assert "down" in by_gr["123456"].message


def test_citation_without_year_that_lawphil_cannot_place_says_why(world):
    world.source.locations = {}  # neither the catalog nor a month scan can place this number
    upload = new_upload(world, "GR no 180046")

    world.resolve.execute(upload.id)

    (citation,) = world.uploads.get(upload.id).citations
    assert citation.status is MatchStatus.NOT_FOUND
    assert "no year was given" in citation.message
    assert world.source.locate_calls == [("180046", None)]  # the locator is always asked; it decides if a year is needed


def test_citation_without_year_is_resolved_when_the_catalog_knows_the_number(world):
    upload = new_upload(world, "Review Center v Ermita, GR no 180046")  # the student wrote no year

    world.resolve.execute(upload.id)

    (citation,) = world.uploads.get(upload.id).citations
    assert citation.status is MatchStatus.MATCH
    assert citation.matched_case_id is not None


def test_progress_is_committed_after_every_citation(world):
    upload = new_upload(world, "GR no 180046 (2009)\nGR no 222222 (2009)")
    before = world.uow.commits

    world.resolve.execute(upload.id)

    assert world.uow.commits - before >= 3  # two citations + the final status


# -- SearchCaseByGrNumber -----------------------------------------------------------


def test_search_returns_stored_cases(world):
    world.cases.add(parse_official_case())
    result = world.search.execute(GR, None)
    assert result.status is SearchStatus.FOUND
    assert [str(c.gr_no) for c in result.cases] == ["180046"]
    assert world.jobs.fetch_calls == []


def test_search_for_unknown_case_with_year_queues_a_background_fetch(world):
    result = world.search.execute(GR, 2009)
    assert (result.status, result.cases) == (SearchStatus.PENDING, [])
    assert world.jobs.fetch_calls == [("180046", 2009)]


def test_search_without_year_asks_for_one_and_queues_nothing(world):
    result = world.search.execute(GR, None)
    assert result.status is SearchStatus.NEEDS_YEAR
    assert world.jobs.fetch_calls == []
