from dataclasses import replace

from caselens.application.use_cases.reparse_stored_cases import ReparseStoredCases
from caselens.infrastructure.lawphil.html_parser import PARSER_VERSION, LawphilCaseParser
from tests.fakes import FakeUnitOfWork, InMemoryCaseRepository
from tests.helpers import OFFICIAL_URL, parse_official_case


def stale_case():
    """A stored case as an old parser left it: no ponente, no statutes, no justices."""
    return replace(
        parse_official_case(),
        parser_version=1,
        ponente=None,
        statutes=[],
        cited_cases=[],
        full_text="old text without the signature table",
    )


def build(repo: InMemoryCaseRepository) -> tuple[ReparseStoredCases, FakeUnitOfWork]:
    uow = FakeUnitOfWork()
    return ReparseStoredCases(repo, LawphilCaseParser(), PARSER_VERSION, uow), uow


def test_stale_case_is_reparsed_in_place_from_its_stored_html():
    repo = InMemoryCaseRepository()
    stored = repo.add(stale_case())
    stored_id = stored.id

    use_case, uow = build(repo)
    report = use_case.execute()

    assert (report.updated, report.failed) == (1, [])
    fixed = repo.get(stored_id)
    assert fixed.id == stored_id  # same id: uploads that point at it stay valid
    assert fixed.parser_version == PARSER_VERSION
    assert fixed.ponente == "CARPIO" and fixed.statutes and "WE CONCUR:" in fixed.full_text
    assert uow.commits == 1


def test_current_cases_are_left_alone():
    repo = InMemoryCaseRepository()
    repo.add(parse_official_case())
    use_case, uow = build(repo)

    report = use_case.execute()

    assert (report.updated, report.failed, uow.commits) == (0, [], 0)


def test_one_unreadable_page_is_reported_and_the_others_still_update():
    repo = InMemoryCaseRepository()
    good = repo.add(stale_case())
    broken = repo.add(replace(stale_case(), source_url="https://lawphil.net/judjuris/x/gr_1_2000.html",
                              raw_html="<html><body><p>no header here</p></body></html>"))

    report = build(repo)[0].execute()

    assert report.updated == 1
    assert [(cid, url) for cid, url, _ in report.failed] == [(broken.id, broken.source_url)]
    assert repo.get(good.id).parser_version == PARSER_VERSION
    assert repo.get(broken.id).parser_version == 1  # stays flagged for a later retry
    assert repo.get(good.id).source_url == OFFICIAL_URL


# -- RefetchDamagedCases ------------------------------------------------------------


def test_damaged_cases_are_downloaded_again_and_fixed_in_place():
    from caselens.application.use_cases.refetch_damaged_cases import RefetchDamagedCases
    from tests.fakes import FixtureCaseSource
    from tests.helpers import official_html

    repo = InMemoryCaseRepository()
    damaged = repo.add(replace(parse_official_case(), raw_html="OSG�s objections", full_text="OSG�s objections"))
    healthy_url = "https://lawphil.net/judjuris/x/gr_1_2000.html"
    healthy = repo.add(replace(parse_official_case(), source_url=healthy_url))
    source = FixtureCaseSource({OFFICIAL_URL: official_html()}, {})
    uow = FakeUnitOfWork()

    report = RefetchDamagedCases(repo, source, LawphilCaseParser(), uow).execute()

    assert (report.repaired, report.failed) == (1, [])
    assert source.fetch_calls == [OFFICIAL_URL]  # only the damaged one was downloaded again
    fixed = repo.get(damaged.id)
    assert "�" not in fixed.raw_html and "Center’s President" in fixed.full_text
    assert repo.get(healthy.id).source_url == healthy_url and uow.commits == 1


def test_a_source_that_is_down_is_reported_and_leaves_the_case_as_it_was():
    from caselens.application.use_cases.refetch_damaged_cases import RefetchDamagedCases
    from tests.fakes import FixtureCaseSource

    repo = InMemoryCaseRepository()
    damaged = repo.add(replace(parse_official_case(), raw_html="x�y"))
    source = FixtureCaseSource({}, {})
    source.down = True

    report = RefetchDamagedCases(repo, source, LawphilCaseParser(), FakeUnitOfWork()).execute()

    assert report.repaired == 0 and [cid for cid, _, _ in report.failed] == [damaged.id]
    assert repo.get(damaged.id).raw_html == "x�y"
