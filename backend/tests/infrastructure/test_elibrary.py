"""The SC E-Library as a second library: its monthly lists, its decision pages, its TLS trust, and the routing between the two
libraries. Real pages saved in tests/fixtures/elibrary (true values in EXPECTED.md)."""
import ssl
from datetime import date
from pathlib import Path

import pytest

from caselens.application.use_cases.fetch_case_by_gr_number import FetchCaseByGrNumber
from caselens.application.use_cases.ingest_case import IngestCase
from caselens.domain.entities import CatalogEntry, IndexPage
from caselens.domain.errors import CaseNotFoundError, InvalidSourceUrlError
from caselens.domain.value_objects import DocType, GrNumber
from caselens.infrastructure.elibrary.case_source import ElibraryCaseSource
from caselens.infrastructure.elibrary.catalog_parser import ElibraryCatalogParser
from caselens.infrastructure.elibrary.catalog_source import ElibraryYearDiscovery
from caselens.infrastructure.elibrary.certificates import INTERMEDIATES, elibrary_ssl_context
from caselens.infrastructure.elibrary.html_parser import ElibraryCaseParser
from caselens.infrastructure.elibrary.url_scheme import ElibraryUrlScheme
from caselens.infrastructure.lawphil.html_parser import PARSER_VERSION, LawphilCaseParser
from caselens.infrastructure.source_router import LibraryRouter
from tests.fakes import FakeUnitOfWork, InMemoryCaseRepository, InMemoryCatalogRepository

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "elibrary"
BASE = "https://elibrary.judiciary.gov.ph"
SCHEME = ElibraryUrlScheme(BASE)
NOBLEZA_URL = f"{BASE}/thebookshelf/showdocs/1/60169"


def page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def parse(doc_id: int):
    return ElibraryCaseParser().parse(page(f"showdocs_{doc_id}.html"), SCHEME.decision_url(doc_id))


# -- addresses --------------------------------------------------------------------------------------------------------------


def test_the_elibrary_addresses():
    assert SCHEME.month_list_url(2015, 3) == f"{BASE}/thebookshelf/docmonth/Mar/2015/1"
    assert SCHEME.is_official_case_url(NOBLEZA_URL)
    assert not SCHEME.is_official_case_url("http://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/60169")  # not https
    assert not SCHEME.is_official_case_url("https://evil.example.com/thebookshelf/showdocs/1/60169")
    assert not SCHEME.is_official_case_url(f"{BASE}/thebookshelf/docmonth/Mar/2015/1")
    assert SCHEME.canonical(f"{BASE}/thebookshelf/showdocsfriendly/1/60169") == NOBLEZA_URL


# -- monthly lists ----------------------------------------------------------------------------------------------------------


def test_the_march_2015_list_gives_every_gr_case_and_counts_the_other_matters():
    parsed = ElibraryCatalogParser(SCHEME).parse(page("docmonth_mar2015.html"), SCHEME.month_list_url(2015, 3))
    assert (len(parsed.entries), parsed.link_rows, parsed.other_kinds, parsed.unreadable) == (81, 94, {"ac": 12, "ocaipi": 1}, 0)
    nobleza = next(e for e in parsed.entries if e.gr_no.value == "193038")
    assert (nobleza.title, nobleza.decision_date, nobleza.source_url, nobleza.source) == (
        "JOSEFINA V. NOBLEZA, PETITIONER, VS. SHIRLEY B. NUEGA, RESPONDENT.", date(2015, 3, 11), NOBLEZA_URL, "elibrary",
    )


def test_a_joint_decision_is_found_under_every_one_of_its_numbers():
    entries = {e.gr_no.value: e for e in ElibraryCatalogParser(SCHEME).parse(page("docmonth_mar2015.html"), "x").entries}
    assert entries["211789"].numbers == ("211789", "211790")  # "G.R. Nos. 211789-90"
    assert entries["171127"].numbers == ("171127", "171217", "171228")  # the others are in the title: "[G.R. No. 171217] ..."
    assert not entries["171127"].title.count("[G.R.")  # the title is the first caption only


def test_an_empty_month_is_empty_not_broken():
    parsed = ElibraryCatalogParser(SCHEME).parse(page("docmonth_jun1995_empty.html"), "x")
    assert parsed.entries == [] and not parsed.looks_broken


def test_every_month_from_1996_to_now_is_listed_without_a_request():
    discovery = ElibraryYearDiscovery(SCHEME, 1996, today=lambda: date(2026, 10, 11))
    assert discovery.years()[0] == 1996 and discovery.years()[-1] == 2026
    assert len(discovery.months(2026)) == 10 and len(discovery.months(2015)) == 12
    assert discovery.months(2015)[2] == IndexPage(2015, 3, SCHEME.month_list_url(2015, 3), "elibrary")


# -- decision pages ---------------------------------------------------------------------------------------------------------


def test_nobleza_v_nuega_is_read_whole():
    case = parse(60169)
    assert (case.gr_no.value, case.numbers, case.decision_date) == ("193038", ("193038",), date(2015, 3, 11))
    assert (case.division, case.doc_type, case.ponente) == ("THIRD DIVISION", DocType.DECISION, "VILLARAMA, JR.")
    assert case.title == "JOSEFINA V. NOBLEZA, PETITIONER, VS. SHIRLEY B. NUEGA, RESPONDENT."
    assert case.disposition.value == "DENIED" and case.parser_version == PARSER_VERSION
    paragraphs = case.full_text.split("\n")
    assert paragraphs[0].startswith("At bar is a petition for review on certiorari of the Decision[^1] dated May 14, 2010")
    assert paragraphs[-2:] == ["SO ORDERED.", "Velasco, Jr. (Chairperson), Peralta, Reyes, and Jardeleza, JJ., concur."]
    assert "NOTICE OF JUDGMENT" not in case.full_text and "June 2, 2015" not in paragraphs[-3:]  # the clerk's notice is not the decision
    assert case.opinions == []


def test_every_footnote_is_read_and_linked_to_its_mark():
    case = parse(60169)
    assert [f.number for f in case.footnotes] == list(range(1, 38))
    assert case.footnotes[0].text.startswith("Rollo, pp. 30-52. Penned by Associate Justice Celia C. Librea-Leagogo")
    assert case.footnotes[-1].text == "Id. at 48-49."
    assert case.footnotes[0].anchor == "fnt1"  # the same anchor names as Lawphil's pages, so the case page links them alike
    assert all(f"[^{n}]" in case.full_text for n in range(1, 38))


def test_a_resolution_and_its_dissent_are_read_apart():
    case = parse(59651)
    assert (case.gr_no.value, case.division, case.doc_type, case.ponente) == ("203655", "SPECIAL THIRD DIVISION", DocType.RESOLUTION, "VELASCO JR.")
    assert case.full_text.split("\n")[-1] == "Leonen, J., I dissent. See separate opinion."  # "N O T I C E OF J U D G M E N T" cut
    assert len(case.footnotes) == 34
    [dissent] = case.opinions
    assert (dissent.kind, dissent.author, len(dissent.footnotes)) == ("dissenting", "LEONEN", 40)
    assert dissent.text.startswith("I dissent.") and dissent.text.endswith("ACCORDINGLY, I vote to GRANT the Motion for Reconsideration.")


def test_a_joint_decision_keeps_both_numbers():
    case = parse(60257)
    assert (case.gr_no.value, case.numbers, case.division, case.ponente) == ("211789", ("211789", "211790"), "EN BANC", "BRION")
    assert case.disposition.value == "GRANTED" and len(case.footnotes) == 48


def test_a_page_that_is_not_a_decision_is_refused():
    from caselens.domain.errors import CaseParseError

    with pytest.raises(CaseParseError):
        ElibraryCaseParser().parse("<html><body>Home page</body></html>", NOBLEZA_URL)


# -- TLS ----------------------------------------------------------------------------------------------------------------------


def test_the_elibrary_is_trusted_with_its_missing_intermediate_and_verification_stays_on():
    context = elibrary_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    assert INTERMEDIATES and all("BEGIN CERTIFICATE" in pem for pem in INTERMEDIATES)
    subjects = [dict(x[0] for x in cert["subject"]).get("commonName") for cert in context.get_ca_certs()]
    assert "GlobalSign GCC R3 EV TLS CA 2025" in subjects


@pytest.mark.live
def test_live_the_elibrary_answers_over_verified_tls():
    import httpx

    response = httpx.get(BASE + "/", verify=elibrary_ssl_context(), timeout=30)
    assert response.status_code == 200


# -- two libraries ----------------------------------------------------------------------------------------------------------


class _Pages:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages, self.asked = pages, []

    def get_text(self, url: str) -> str | None:
        self.asked.append(url)
        return self.pages.get(url)


class _Lawphil:
    """Lawphil with nothing for the number (as for G.R. 193038)."""

    def __init__(self, urls=None) -> None:
        self.urls = urls or {}

    def locate(self, gr_no, claimed_year):
        return self.urls.get(gr_no.value, [])

    def fetch(self, url):
        raise CaseNotFoundError(url)


def _catalog_with_nobleza() -> InMemoryCatalogRepository:
    catalog = InMemoryCatalogRepository()
    entries = ElibraryCatalogParser(SCHEME).parse(page("docmonth_mar2015.html"), SCHEME.month_list_url(2015, 3)).entries
    catalog.replace_month(IndexPage(2015, 3, SCHEME.month_list_url(2015, 3), "elibrary"), entries)
    return catalog


def _router(lawphil, pages) -> LibraryRouter:
    elibrary = ElibraryCaseSource(pages, SCHEME, _catalog_with_nobleza())
    return LibraryRouter(lawphil, LawphilCaseParser(), elibrary, ElibraryCaseParser(), SCHEME)


def test_a_number_lawphil_lacks_is_found_and_read_from_the_elibrary():
    pages = _Pages({NOBLEZA_URL: page("showdocs_60169.html")})
    router = _router(_Lawphil(), pages)
    cases = InMemoryCaseRepository()
    case = FetchCaseByGrNumber(router, IngestCase(router, router, cases, FakeUnitOfWork()), cases).execute(GrNumber("193038"), None)
    assert case.source_url == NOBLEZA_URL and case.title.startswith("JOSEFINA V. NOBLEZA") and len(case.footnotes) == 37
    assert pages.asked == [NOBLEZA_URL]


def test_a_number_lawphil_has_is_read_from_lawphil_only():
    lawphil_url = "https://lawphil.net/judjuris/juri2015/mar2015/gr_193038_2015.html"
    router = _router(_Lawphil({"193038": [lawphil_url]}), _Pages({}))
    assert router.locate(GrNumber("193038"), None) == [lawphil_url]


def test_a_number_neither_library_has_is_not_found():
    router = _router(_Lawphil(), _Pages({}))
    cases = InMemoryCaseRepository()
    fetch = FetchCaseByGrNumber(router, IngestCase(router, router, cases, FakeUnitOfWork()), cases)
    with pytest.raises(CaseNotFoundError, match="nor on the SC E-Library"):
        fetch.execute(GrNumber("999999"), 2015)


def test_each_page_is_read_by_its_own_library():
    router = _router(_Lawphil(), _Pages({}))
    assert router.parse(page("showdocs_60169.html"), NOBLEZA_URL).gr_no.value == "193038"
    with pytest.raises(InvalidSourceUrlError):
        ElibraryCaseSource(_Pages({}), SCHEME, InMemoryCatalogRepository()).fetch("https://lawphil.net/judjuris/x.html")


def test_lawphil_never_opens_an_elibrary_row_of_the_catalog():
    from caselens.infrastructure.lawphil.case_source import LawphilCaseSource
    from caselens.infrastructure.lawphil.url_scheme import LawphilUrlScheme

    lawphil = LawphilCaseSource(_Pages({}), None, LawphilUrlScheme("https://lawphil.net"), catalog=_catalog_with_nobleza())
    assert lawphil.locate(GrNumber("193038"), None) == []


def test_an_elibrary_row_carries_its_source():
    entry = CatalogEntry(GrNumber("193038"), ("193038",), "A v. B", None, NOBLEZA_URL, "x", source="elibrary")
    assert entry.source == "elibrary"


# -- naming the library -------------------------------------------------------------------------------------------------------


def test_a_case_read_from_the_elibrary_names_it_on_screen_and_in_its_word_files():
    from caselens.infrastructure.source_notice import court_text_notice, digest_notice
    from caselens.presentation.api.schemas import Attribution

    lawphil_url = "https://lawphil.net/judjuris/juri2009/apr2009/gr_180046_2009.html"
    assert "Supreme Court E-Library" in Attribution.for_url(NOBLEZA_URL).source
    assert "printed copy" in Attribution.for_url(NOBLEZA_URL).notice
    assert Attribution.for_url(lawphil_url) == Attribution()  # Lawphil's as before
    assert "Supreme Court E-Library" in digest_notice(NOBLEZA_URL) and "Lawphil" not in digest_notice(NOBLEZA_URL)
    assert "Lawphil" in digest_notice(lawphil_url) and "E-Library" not in digest_notice(lawphil_url)
    both = court_text_notice([lawphil_url, NOBLEZA_URL])
    assert "Lawphil" in both and "E-Library" in both


def test_the_philippine_reports_citation_is_read_from_an_elibrary_page_only():
    from caselens.infrastructure.elibrary.html_parser import philippine_reports_citation

    assert philippine_reports_citation(page("showdocs_60169.html")) == "755 Phil. 656"
    assert philippine_reports_citation(page("showdocs_59651.html")) == "756 Phil. 354"
    assert philippine_reports_citation("<html><body><h2>EN BANC</h2></body></html>") is None


def test_a_heading_that_only_repeats_its_section_is_dropped_and_a_real_label_kept():
    from caselens.domain.digest_v2 import Section, block_heading

    assert block_heading(Section.DOCTRINE, "Doctrine") is None and block_heading(Section.CASE_SUMMARY, "Case Summary:") is None
    assert block_heading(Section.DOCTRINE, "1. Community property does not depend on contribution") == "1. Community property does not depend on contribution"
    assert block_heading(Section.FACTS, None) is None
