"""Repositories against the real PostgreSQL (rolled back after each test)."""
from datetime import date

import pytest

from caselens.domain.entities import Upload, UploadedCitation
from caselens.domain.errors import DuplicateCaseError
from caselens.domain.services.citation_extractor import GrCitationExtractor
from caselens.domain.services.citation_matcher import CitationMatcher
from caselens.domain.value_objects import Disposition, DocType, GrNumber, MatchStatus
from caselens.infrastructure.db.repositories import SqlCaseRepository, SqlUploadRepository
from tests.helpers import OFFICIAL_URL, parse_official_case

pytestmark = pytest.mark.db


def test_case_round_trips_with_footnotes_opinion_statutes_and_citations(db_session):
    repo = SqlCaseRepository(db_session)
    original = parse_official_case()

    stored = repo.add(original)
    db_session.expire_all()
    loaded = repo.get(stored.id)

    assert loaded.id == stored.id and loaded.fetched_at is not None
    assert (str(loaded.gr_no), loaded.decision_date, loaded.ponente) == ("180046", date(2009, 4, 2), "CARPIO")
    assert loaded.doc_type is DocType.DECISION and loaded.disposition is Disposition.GRANTED
    assert loaded.raw_html == original.raw_html and loaded.full_text == original.full_text
    assert [f.number for f in loaded.footnotes] == list(range(1, 43))
    assert [f.text for f in loaded.footnotes] == [f.text for f in original.footnotes]
    assert len(loaded.opinions) == 1
    assert loaded.opinions[0].author == "BRION"
    assert [f.number for f in loaded.opinions[0].footnotes] == list(range(1, 14))
    assert loaded.statutes == original.statutes
    assert loaded.cited_cases == original.cited_cases


def test_lookups(db_session):
    repo = SqlCaseRepository(db_session)
    stored = repo.add(parse_official_case())

    assert [c.id for c in repo.find_by_gr_no(GrNumber("180046"))] == [stored.id]
    assert repo.find_by_gr_no(GrNumber("999999")) == []
    assert repo.get_by_source_url(OFFICIAL_URL).id == stored.id
    assert repo.get_by_source_url("https://lawphil.net/nope.html") is None
    assert repo.get(10**9) is None
    found = repo.summaries([stored.id, 10**9])
    assert list(found) == [stored.id]
    assert (found[stored.id].source_url, found[stored.id].title[:13], found[stored.id].ponente) == (
        OFFICIAL_URL, "REVIEW CENTER", "CARPIO",
    )
    assert repo.summaries([]) == {}


def test_duplicate_source_url_raises_and_leaves_the_session_usable(db_session):
    repo = SqlCaseRepository(db_session)
    repo.add(parse_official_case())

    with pytest.raises(DuplicateCaseError):
        repo.add(parse_official_case())

    assert len(repo.find_by_gr_no(GrNumber("180046"))) == 1  # session still works, one row only


def test_upload_round_trip_and_result_update(db_session):
    cases, uploads = SqlCaseRepository(db_session), SqlUploadRepository(db_session)
    case = cases.add(parse_official_case())
    text = "Review Center v Ermita, 538 SCRA 428, GR no 180046 (April 2, 2010)"
    upload = uploads.add(
        Upload("sample.pdf", text, [UploadedCitation(c) for c in GrCitationExtractor().extract(text)])
    )
    assert upload.id and upload.citations[0].id and upload.created_at

    db_session.expire_all()
    loaded = uploads.get(upload.id)
    claimed = loaded.citations[0].claimed
    assert (claimed.title, claimed.claimed_year, claimed.claimed_date, claimed.reporter) == (
        "Review Center v Ermita", 2010, date(2010, 4, 2), "538 SCRA 428",
    )
    assert loaded.citations[0].status is MatchStatus.PENDING

    citation = loaded.citations[0]
    citation.record_match(CitationMatcher().match(citation.claimed, case), case.id)
    loaded.status = "done"
    uploads.save(loaded)

    db_session.expire_all()
    final = uploads.get(upload.id)
    assert final.status == "done"
    assert final.citations[0].status is MatchStatus.MISMATCH
    assert final.citations[0].mismatches == {"year": {"claimed": 2010, "official": 2009}}
    assert final.citations[0].unverified == ["reporter"]
    assert final.citations[0].matched_case_id == case.id


def test_update_content_replaces_children_in_place_and_keeps_upload_links(db_session):
    from dataclasses import replace

    cases, uploads = SqlCaseRepository(db_session), SqlUploadRepository(db_session)
    stale = replace(parse_official_case(), parser_version=1, ponente=None, statutes=[],
                    cited_cases=[], footnotes=[], opinions=[])
    stored = cases.add(stale)
    text = "GR no 180046 (2009)"
    upload = uploads.add(Upload("a.pdf", text, [UploadedCitation(c) for c in GrCitationExtractor().extract(text)]))
    upload.citations[0].record_match(CitationMatcher().match(upload.citations[0].claimed, stored), stored.id)
    uploads.save(upload)

    assert [(i, u) for i, u, _ in cases.outdated(2)] == [(stored.id, OFFICIAL_URL)]

    cases.update_content(stored.id, parse_official_case())  # current parser output
    db_session.expire_all()

    fixed = cases.get(stored.id)
    assert fixed.id == stored.id and fixed.ponente == "CARPIO"
    assert len(fixed.footnotes) == 42 and len(fixed.opinions) == 1
    assert len(fixed.opinions[0].footnotes) == 13  # opinion footnotes re-attached to the new opinion row
    assert fixed.statutes and fixed.cited_cases
    assert cases.outdated(2) == []
    assert uploads.get(upload.id).citations[0].matched_case_id == stored.id  # link survived


def test_updating_twice_does_not_duplicate_children(db_session):
    cases = SqlCaseRepository(db_session)
    stored = cases.add(parse_official_case())
    cases.update_content(stored.id, parse_official_case())
    cases.update_content(stored.id, parse_official_case())
    db_session.expire_all()
    again = cases.get(stored.id)
    assert (len(again.footnotes), len(again.opinions), len(again.opinions[0].footnotes)) == (42, 1, 13)


def test_unknown_upload_is_none(db_session):
    assert SqlUploadRepository(db_session).get(10**9) is None
