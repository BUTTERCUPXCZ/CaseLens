"""Use cases added for the web app: recent uploads, case library, attach a pasted link, retry."""
from dataclasses import replace
from datetime import date

import pytest

from caselens.domain.entities import Upload, UploadedCitation
from caselens.domain.errors import CaseNotFoundError, InvalidSourceUrlError
from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.domain.value_objects import MatchStatus
from tests.helpers import OFFICIAL_URL, parse_official_case
from tests.world import World


@pytest.fixture
def world() -> World:
    return World()


def new_upload(world: World, text: str, name: str = "x.pdf") -> Upload:
    claims = GrCitationExtractor().extract(text)
    return world.uploads.add(Upload(name, text, [UploadedCitation(c) for c in claims]))


# -- ListUploads --------------------------------------------------------------------


def test_recent_uploads_are_newest_first_with_counts_per_state(world):
    first = new_upload(world, "GR no 180046 (2009)", "old.pdf")
    second = new_upload(world, "GR no 180046 (2009)\nGR no 222222 (2009)", "new.pdf")
    world.resolve.execute(second.id)  # 180046 found, 222222 not found
    assert first.id < second.id

    summaries = world.list_uploads.execute(limit=10)

    assert [s.filename for s in summaries] == ["new.pdf", "old.pdf"]
    newest = summaries[0]
    assert (newest.total, newest.matched, newest.not_found, newest.pending) == (2, 1, 1, 0)
    assert summaries[1].pending == 1  # never resolved


def test_recent_uploads_respect_the_limit(world):
    for n in range(3):
        new_upload(world, f"GR no 18004{n} (2009)", f"{n}.pdf")
    assert len(world.list_uploads.execute(limit=2)) == 2


# -- ListCases ----------------------------------------------------------------------


def seed_cases(world: World) -> None:
    template = parse_official_case()
    for n, (title, year) in enumerate([("ALPHA CORP vs. BETA", 2008), ("GAMMA INC vs. DELTA", 2010), ("EPSILON vs. ZETA", None)]):
        world.cases.add(
            replace(
                template,
                gr_no=type(template.gr_no)(f"20000{n}"),
                source_url=f"https://lawphil.net/judjuris/x/gr_20000{n}.html",
                title=title,
                decision_date=date(year, 1, 1) if year else None,
            )
        )


def test_library_lists_newest_decision_first_and_pages(world):
    seed_cases(world)
    page = world.list_cases.execute(None, limit=2, offset=0)
    assert [c.title for c in page.items] == ["GAMMA INC vs. DELTA", "ALPHA CORP vs. BETA"]
    assert (page.total, page.limit, page.offset) == (3, 2, 0)

    rest = world.list_cases.execute(None, limit=2, offset=2)
    assert [c.title for c in rest.items] == ["EPSILON vs. ZETA"]  # undated last


def test_library_search_matches_name_or_start_of_gr_number(world):
    seed_cases(world)
    assert [c.title for c in world.list_cases.execute("gamma", 10, 0).items] == ["GAMMA INC vs. DELTA"]
    by_number = world.list_cases.execute("20000", 10, 0).items
    assert [str(c.gr_no) for c in by_number] == ["200001", "200000", "200002"]  # 2010, 2008, undated
    assert world.list_cases.execute("nothing like this", 10, 0).total == 0


def test_blank_search_means_everything(world):
    seed_cases(world)
    assert world.list_cases.execute("   ", 10, 0).total == 3


# -- AttachCaseToCitation -----------------------------------------------------------


def test_pasted_link_resolves_a_citation_that_had_no_year(world):
    world.source.locations = {}  # the lists cannot place this number, so only the pasted link can
    upload = new_upload(world, "Review Center v Ermita, GR no 180046")
    world.resolve.execute(upload.id)
    citation = world.uploads.get(upload.id).citations[0]
    assert citation.status is MatchStatus.NOT_FOUND  # no year, so it could not be searched

    world.attach.execute(upload.id, citation.id, OFFICIAL_URL)

    done = world.uploads.get(upload.id)
    assert done.citations[0].status is MatchStatus.MATCH
    assert done.citations[0].matched_case_id is not None
    assert done.status == "done"


def test_pasting_the_wrong_case_is_reported_not_accepted(world):
    upload = new_upload(world, "GR no 999999")
    citation = upload.citations[0]

    world.attach.execute(upload.id, citation.id, OFFICIAL_URL)  # but this is GR 180046

    assert world.uploads.get(upload.id).citations[0].mismatches["gr_no"] == {
        "claimed": "999999", "official": "180046",
    }


def test_attach_to_unknown_upload_or_citation_is_not_found(world):
    upload = new_upload(world, "GR no 180046")
    with pytest.raises(CaseNotFoundError):
        world.attach.execute(999, 1, OFFICIAL_URL)
    with pytest.raises(CaseNotFoundError):
        world.attach.execute(upload.id, 999, OFFICIAL_URL)


def test_attach_rejects_links_that_are_not_official_pages(world):
    world.source.fetch = lambda url: (_ for _ in ()).throw(InvalidSourceUrlError(url))
    upload = new_upload(world, "GR no 180046")
    with pytest.raises(InvalidSourceUrlError):
        world.attach.execute(upload.id, upload.citations[0].id, "https://evil.example/x.html")
    assert world.uploads.get(upload.id).citations[0].status is MatchStatus.PENDING  # untouched


# -- RetryUpload --------------------------------------------------------------------


def test_retry_rechecks_only_the_citations_that_failed_to_check(world):
    text = "GR no 180046 (April 2, 2009)\nGR no 123456 (2001)\nGR no 222222 (2009)"
    upload = new_upload(world, text)
    world.source.down_for = {"123456"}
    world.resolve.execute(upload.id)
    statuses = {str(c.claimed.gr_number): c.status for c in world.uploads.get(upload.id).citations}
    assert statuses == {"180046": MatchStatus.MATCH, "123456": MatchStatus.ERROR, "222222": MatchStatus.NOT_FOUND}

    world.retry.execute(upload.id)

    after = {str(c.claimed.gr_number): c.status for c in world.uploads.get(upload.id).citations}
    assert after == {"180046": MatchStatus.MATCH, "123456": MatchStatus.PENDING, "222222": MatchStatus.NOT_FOUND}
    assert world.uploads.get(upload.id).status == "processing"
    assert world.jobs.resolve_upload_ids[-1] == upload.id


def test_retry_with_nothing_to_retry_queues_nothing(world):
    upload = new_upload(world, "GR no 180046 (2009)")
    world.resolve.execute(upload.id)
    queued_before = list(world.jobs.resolve_upload_ids)

    world.retry.execute(upload.id)

    assert world.jobs.resolve_upload_ids == queued_before


def test_retry_unknown_upload_is_not_found(world):
    with pytest.raises(CaseNotFoundError):
        world.retry.execute(999)
