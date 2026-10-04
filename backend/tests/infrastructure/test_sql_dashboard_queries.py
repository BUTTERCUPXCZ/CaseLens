"""The library search and the recent-uploads summary against real PostgreSQL."""
from dataclasses import replace
from datetime import date

import pytest

from caselens.domain.entities import Upload, UploadedCitation
from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.domain.value_objects import GrNumber, MatchStatus
from caselens.infrastructure.db.repositories import SqlCaseRepository, SqlUploadRepository
from tests.helpers import parse_official_case

pytestmark = pytest.mark.db


def seed(session) -> SqlCaseRepository:
    """Three SYNTHETIC cases (real parsed GR 180046 with other names/numbers/dates)."""
    repo = SqlCaseRepository(session)
    template = parse_official_case()
    for number, title, when in [
        ("181111", "ALPHA CORP vs. BETA 100% LTD", date(2008, 1, 1)),
        ("182222", "GAMMA INC vs. DELTA", date(2010, 1, 1)),
        ("183333", "EPSILON vs. ZETA", None),
    ]:
        repo.add(replace(template, gr_no=GrNumber(number), title=title, decision_date=when,
                         source_url=f"https://lawphil.net/judjuris/x/gr_{number}.html"))
    return repo


def test_search_without_a_query_pages_newest_decision_first_undated_last(db_session):
    repo = seed(db_session)
    items, total = repo.search(None, limit=2, offset=0)
    assert (total, [str(c.gr_no) for c in items]) == (3, ["182222", "181111"])
    rest, _ = repo.search(None, limit=2, offset=2)
    assert [str(c.gr_no) for c in rest] == ["183333"]


@pytest.mark.parametrize(
    "query, expected",
    [
        ("gamma", ["182222"]),            # part of the name, any case
        ("18", ["182222", "181111", "183333"]),   # start of the G.R. number
        ("G.R. No. 1822", ["182222"]),    # the way a student would type it
        ("gr 1811", ["181111"]),
        ("nope", []),
    ],
)
def test_search_by_name_or_start_of_gr_number(db_session, query, expected):
    items, total = seed(db_session).search(query, limit=10, offset=0)
    assert [str(c.gr_no) for c in items] == expected and total == len(expected)


def test_a_typed_percent_sign_is_not_a_wildcard(db_session):
    repo = seed(db_session)
    assert [str(c.gr_no) for c in repo.search("100%", 10, 0)[0]] == ["181111"]  # the literal "100%"
    assert repo.search("%", 10, 0)[1] == 1  # only the title that really contains "%"
    assert repo.search("_", 10, 0)[1] == 0  # underscore is literal too, not "any character"


def test_search_summaries_carry_no_text_but_the_fields_a_list_needs(db_session):
    items, _ = seed(db_session).search("gamma", 10, 0)
    summary = items[0]
    assert (summary.title, summary.ponente, summary.disposition.value, summary.source_url) == (
        "GAMMA INC vs. DELTA", "CARPIO", "GRANTED", "https://lawphil.net/judjuris/x/gr_182222.html",
    )
    assert not hasattr(summary, "full_text") and not hasattr(summary, "raw_html")


def test_recent_uploads_count_each_state_and_include_uploads_without_citations(db_session):
    cases, uploads = seed(db_session), SqlUploadRepository(db_session)
    official = SqlCaseRepository(db_session).add(parse_official_case())

    text = "GR no 180046 (2009)\nGR no 123456 (2001)\nGR no 222222 (2001)"
    first = uploads.add(Upload("a.pdf", text, [UploadedCitation(c) for c in GrCitationExtractor().extract(text)]))
    c0, c1, _ = first.citations
    c0.record_match(CitationMatcher().match(c0.claimed, official), official.id)       # match
    c1.record_failure(MatchStatus.NOT_FOUND, "not on Lawphil")                          # not found
    first.status = "done"
    uploads.save(first)
    empty = uploads.add(Upload("empty.docx", "no citations here"))                      # no citations

    summaries = uploads.list_recent(10)

    assert [s.filename for s in summaries] == ["empty.docx", "a.pdf"]  # newest first
    a = summaries[1]
    assert (a.total, a.matched, a.needs_look, a.not_found, a.errors, a.pending) == (3, 1, 0, 1, 0, 1)
    assert a.status == "done" and a.created_at is not None
    assert (summaries[0].id, summaries[0].total) == (empty.id, 0)
    assert len(uploads.list_recent(1)) == 1
