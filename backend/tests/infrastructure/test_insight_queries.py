"""Trend SQL against PostgreSQL.

The six cases below are SYNTHETIC: real parsed GR 180046 copied with different URLs,
dates, ponentes, rulings and statutes so every count is known in advance.
"""
from dataclasses import replace
from datetime import date

import pytest

from caselens.application.use_cases.get_trends import GetTrends
from caselens.domain.entities import CitedCase, Statute
from caselens.domain.value_objects import Disposition, DocType, GrNumber, StatuteType
from caselens.infrastructure.db.insight_queries import SqlInsightQueries
from caselens.infrastructure.db.repositories import SqlCaseRepository
from tests.helpers import parse_official_case

pytestmark = pytest.mark.db

RA7722 = Statute(StatuteType.REPUBLIC_ACT, "7722", "RA 7722")
RA8981 = Statute(StatuteType.REPUBLIC_ACT, "8981", "RA 8981")
EO292 = Statute(StatuteType.EXECUTIVE_ORDER, "292", "EO 292")
OPLE = CitedCase("Ople v. Torres", "127685", "footnote", 3)
OPLE_BODY = CitedCase("ople  v. torres", None, "body")  # same case, different spacing/case
LACAP = CitedCase("Republic v. Lacap", "158253", "footnote", 5)


def seed(session) -> SqlCaseRepository:
    repo = SqlCaseRepository(session)
    template = parse_official_case()

    def add(n, ponente, year, disposition, statutes, cited, doc_type=DocType.DECISION):
        repo.add(
            replace(
                template,
                gr_no=GrNumber(f"1000{n}0"),
                source_url=f"https://lawphil.net/judjuris/juri{year}/x/gr_1000{n}0_{year}.html",
                ponente=ponente,
                decision_date=date(year, 6, 1),
                disposition=disposition,
                doc_type=doc_type,
                statutes=statutes,
                cited_cases=cited,
                opinions=[],
                footnotes=[],
            )
        )

    add(1, "CARPIO", 2009, Disposition.GRANTED, [RA7722, RA8981], [OPLE])
    add(2, "CARPIO", 2009, Disposition.DENIED, [RA7722], [OPLE_BODY, LACAP])
    add(3, "TINGA", 2009, Disposition.GRANTED, [RA7722, EO292], [OPLE])
    add(4, "TINGA", 2010, Disposition.GRANTED, [EO292], [])
    add(5, "BRION", 2010, Disposition.DISMISSED, [RA8981], [LACAP])
    add(6, "BRION", 2010, Disposition.GRANTED, [RA7722], [], doc_type=DocType.RESOLUTION)  # ignored
    return repo


def test_top_statutes_count_cases_not_mentions(db_session):
    seed(db_session)
    result = SqlInsightQueries(db_session).top_statutes(10)
    assert [(s.statute_type, s.number, s.cases) for s in result] == [
        ("RA", "7722", 3),  # cases 1, 2, 3 (case 6 is a resolution, not counted)
        ("EO", "292", 2),
        ("RA", "8981", 2),
    ]
    assert len(SqlInsightQueries(db_session).top_statutes(1)) == 1


def test_dispositions_by_year(db_session):
    seed(db_session)
    result = SqlInsightQueries(db_session).dispositions_by_year()
    assert [(d.year, d.disposition, d.cases) for d in result] == [
        (2009, "DENIED", 1),
        (2009, "GRANTED", 2),
        (2010, "DISMISSED", 1),
        (2010, "GRANTED", 1),
    ]


def test_most_cited_cases_merges_spacing_and_case_variants(db_session):
    seed(db_session)
    result = SqlInsightQueries(db_session).most_cited_cases(10)
    assert [(c.title.lower().replace("  ", " "), c.gr_no, c.cases) for c in result] == [
        ("ople v. torres", "127685", 3),  # GR kept from the footnote form
        ("republic v. lacap", "158253", 2),
    ]


def test_cases_per_ponente(db_session):
    seed(db_session)
    result = SqlInsightQueries(db_session).cases_per_ponente(10)
    assert [(p.ponente, p.cases) for p in result] == [("CARPIO", 2), ("TINGA", 2), ("BRION", 1)]
    # most first; ties alphabetical


def test_total_counts_only_decisions(db_session):
    seed(db_session)
    assert SqlInsightQueries(db_session).total_cases() == 5


def test_trends_report_is_flagged_not_enough_below_the_minimum(db_session):
    repo = SqlCaseRepository(db_session)
    repo.add(parse_official_case())  # one real decision

    report = GetTrends(SqlInsightQueries(db_session)).execute()

    assert (report.total_cases, report.minimum_cases, report.enough_data) == (1, 5, False)
    assert report.top_statutes  # counts are still returned; the flag tells the reader how to treat them


def test_trends_report_is_enough_at_the_minimum(db_session):
    seed(db_session)
    report = GetTrends(SqlInsightQueries(db_session)).execute()
    assert (report.total_cases, report.enough_data) == (5, True)
