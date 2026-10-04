"""In-memory stand-ins for ports. Using them proves the use cases only depend on the
port (Liskov): the same code runs against SQL or a dict."""
from caselens.application.ports.ai import AnswerChecker, AnswerWriter
from caselens.application.ports.digests import DigestRepository
from caselens.application.ports.gateways import CaseFetcher, CaseLocator, JobQueue
from caselens.application.ports.locks import JobLockRepository
from caselens.application.ports.repositories import (
    CaseRepository,
    MonthIndexRepository,
    UnitOfWork,
    UploadRepository,
)
from caselens.domain.case_digest import CaseDigest
from caselens.domain.digest import CheckResult, Verdict
from caselens.domain.entities import Case, CaseSummary, Upload, UploadSummary
from caselens.domain.errors import CaseNotFoundError, DuplicateCaseError, SourceUnavailableError
from caselens.domain.value_objects import GrNumber, MatchStatus


class InMemoryMonthIndexRepository(MonthIndexRepository):
    def __init__(self) -> None:
        self.data: dict[str, list[str]] = {}

    def get(self, url: str) -> list[str] | None:
        return self.data.get(url)

    def save(self, url: str, case_urls: list[str]) -> None:
        self.data[url] = list(case_urls)


class InMemoryCaseRepository(CaseRepository):
    def __init__(self) -> None:
        self.cases: dict[int, Case] = {}
        self.fail_with_duplicate_once = False

    def add(self, case: Case) -> Case:
        if self.fail_with_duplicate_once:
            self.fail_with_duplicate_once = False
            raise DuplicateCaseError(case.source_url)
        case.id = len(self.cases) + 1
        self.cases[case.id] = case
        return case

    def get(self, case_id: int) -> Case | None:
        return self.cases.get(case_id)

    def get_by_source_url(self, url: str) -> Case | None:
        return next((c for c in self.cases.values() if c.source_url == url), None)

    def find_by_gr_no(self, gr_no: GrNumber) -> list[Case]:
        return [c for c in self.cases.values() if c.gr_no == gr_no]

    def summaries(self, case_ids: list[int]) -> dict[int, CaseSummary]:
        return {i: self._summary(self.cases[i]) for i in case_ids if i in self.cases}

    @staticmethod
    def _summary(c: Case) -> CaseSummary:
        return CaseSummary(c.id, c.gr_no, c.title, c.decision_date, c.doc_type, c.ponente,
                           c.division, c.disposition, c.source_url)

    def outdated(self, current_parser_version: int) -> list[tuple[int, str, str]]:
        return [
            (c.id, c.source_url, c.raw_html)
            for c in self.cases.values()
            if c.parser_version < current_parser_version
        ]

    def with_damaged_text(self) -> list[tuple[int, str]]:
        return [(c.id, c.source_url) for c in self.cases.values() if "\ufffd" in c.raw_html]

    def update_content(self, case_id: int, parsed: Case) -> None:
        parsed.id = case_id
        self.cases[case_id] = parsed

    def search(self, query: str | None, limit: int, offset: int) -> tuple[list[CaseSummary], int]:
        def matches(case: Case) -> bool:
            if not query:
                return True
            return query.lower() in (case.title or "").lower() or str(case.gr_no).startswith(query)

        found = [c for c in self.cases.values() if matches(c)]
        found.sort(key=lambda c: (c.decision_date is not None, c.decision_date, c.id), reverse=True)
        summaries = [
            CaseSummary(c.id, c.gr_no, c.title, c.decision_date, c.doc_type, c.ponente,
                        c.division, c.disposition, c.source_url)
            for c in found
        ]
        return summaries[offset : offset + limit], len(summaries)


class InMemoryUploadRepository(UploadRepository):
    def __init__(self) -> None:
        self.uploads: dict[int, Upload] = {}
        self._next_citation_id = 1

    def add(self, upload: Upload) -> Upload:
        upload.id = len(self.uploads) + 1
        for citation in upload.citations:
            citation.id = self._next_citation_id
            self._next_citation_id += 1
        self.uploads[upload.id] = upload
        return upload

    def get(self, upload_id: int) -> Upload | None:
        return self.uploads.get(upload_id)

    def get_file_data(self, upload_id: int) -> bytes | None:
        upload = self.uploads.get(upload_id)
        return upload.file_data if upload else None

    def save(self, upload: Upload) -> None:
        self.uploads[upload.id] = upload

    def list_recent(self, limit: int) -> list[UploadSummary]:
        def count(upload: Upload, status: MatchStatus) -> int:
            return sum(1 for c in upload.citations if c.status is status)

        newest_first = sorted(self.uploads.values(), key=lambda u: u.id, reverse=True)[:limit]
        return [
            UploadSummary(
                id=u.id, filename=u.filename, status=u.status, created_at=u.created_at,
                matched=count(u, MatchStatus.MATCH), needs_look=count(u, MatchStatus.MISMATCH),
                not_found=count(u, MatchStatus.NOT_FOUND), errors=count(u, MatchStatus.ERROR),
                pending=count(u, MatchStatus.PENDING),
            )
            for u in newest_first
        ]


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class FakeJobQueue(JobQueue):
    def __init__(self) -> None:
        self.resolve_upload_ids: list[int] = []
        self.fetch_calls: list[tuple[str, int | None]] = []
        self.digest_builds: list[tuple[int, list[str] | None]] = []
        self.catalog_builds: list[int] = []
        self.catalog_refreshes = 0
        self.catalog_refresh_locked = False
        self.catalog_build_running = False

    def enqueue_build_digest(self, digest_id: int, keys: list[str] | None = None) -> None:
        self.digest_builds.append((digest_id, keys))

    def enqueue_refresh_catalog(self) -> bool:
        if self.catalog_refresh_locked:
            return False
        self.catalog_refreshes += 1
        self.catalog_refresh_locked = True
        return True

    def enqueue_build_catalog(self, first_year: int) -> bool:
        if self.catalog_build_running:
            return False
        self.catalog_builds.append(first_year)
        return True

    def enqueue_resolve_upload(self, upload_id: int) -> None:
        self.resolve_upload_ids.append(upload_id)

    def enqueue_fetch_case(self, gr_no: str, year: int | None) -> None:
        self.fetch_calls.append((gr_no, year))


class FixtureCaseSource(CaseLocator, CaseFetcher):
    """Serves saved pages instead of lawphil.net."""

    def __init__(self, pages: dict[str, str], locations: dict[str, list[str]]) -> None:
        self.pages = pages
        self.locations = locations
        self.locate_calls: list[tuple[str, int | None]] = []
        self.fetch_calls: list[str] = []
        self.down = False
        self.down_for: set[str] = set()  # G.R. numbers whose lookup fails (simulated outage)

    def locate(self, gr_no: GrNumber, claimed_year: int | None) -> list[str]:
        self.locate_calls.append((str(gr_no), claimed_year))
        if self.down or str(gr_no) in self.down_for:
            raise SourceUnavailableError("Lawphil is down (simulated)")
        return self.locations.get(str(gr_no), [])

    def fetch(self, url: str) -> str:
        self.fetch_calls.append(url)
        if self.down:
            raise SourceUnavailableError("Lawphil is down (simulated)")
        if url not in self.pages:
            raise CaseNotFoundError(url)
        return self.pages[url]


# -- catalog fakes ------------------------------------------------------------------

from caselens.application.ports.catalog import CatalogIndexParser, CatalogRepository, IndexFetcher, ParsedIndex, YearDiscovery  # noqa: E402
from caselens.domain.entities import CatalogEntry, CatalogHit, CatalogStatus, IndexPage  # noqa: E402


class FakeYearDiscovery(YearDiscovery):
    def __init__(self, months_by_year: dict[int, list[int]]) -> None:
        self.months_by_year = months_by_year
        self.months_asked: list[int] = []
        self.failing_years: set[int] = set()

    def years(self) -> list[int]:
        return sorted(self.months_by_year)

    def months(self, year: int) -> list[IndexPage]:
        self.months_asked.append(year)
        if year in self.failing_years:
            raise SourceUnavailableError(f"year page {year} is down (simulated)")
        return [IndexPage(year, m, page_url(year, m)) for m in self.months_by_year.get(year, [])]


def page_url(year: int, month: int) -> str:
    code = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"][month - 1]
    return f"https://lawphil.net/judjuris/juri{year}/{code}{year}/{code}{year}.html"


class FakeIndexFetcher(IndexFetcher):
    """Serves a page body per URL; None for a page that does not exist; raises for a down page."""

    def __init__(self, pages: dict[str, str | None] | None = None, default: str | None = "<page/>") -> None:
        self.pages = pages or {}
        self.default = default
        self.fetched: list[str] = []
        self.down: set[str] = set()

    def fetch(self, url: str) -> str | None:
        self.fetched.append(url)
        if url in self.down:
            raise SourceUnavailableError(f"{url} is down (simulated)")
        return self.pages.get(url, self.default)


class FakeCatalogParser(CatalogIndexParser):
    """One decision per page unless told otherwise; `broken_pages` parse as 'links but nothing readable'."""

    def __init__(self) -> None:
        self.broken_pages: set[str] = set()
        self.entries_per_page = 1

    def parse(self, html: str, index_url: str) -> ParsedIndex:
        if index_url in self.broken_pages:
            return ParsedIndex([], link_rows=5, unreadable=5)
        entries = [
            CatalogEntry(GrNumber(str(100000 + i)), (str(100000 + i),), f"Party {i} vs. Other", None, f"{index_url}#{i}", index_url)
            for i in range(self.entries_per_page)
        ]
        return ParsedIndex(entries, link_rows=len(entries))


class InMemoryCatalogRepository(CatalogRepository):
    def __init__(self) -> None:
        self.months: dict[tuple[int, int], str] = {}
        self.entries: dict[tuple[int, int], list[CatalogEntry]] = {}
        self.writes: list[tuple[int, int]] = []

    def mark_absent(self, page: IndexPage) -> None:
        self.months[(page.year, page.month)] = "absent"

    def register_months(self, pages: list[IndexPage]) -> None:
        for page in pages:
            self.months.setdefault((page.year, page.month), "pending")

    def replace_month(self, page: IndexPage, entries: list[CatalogEntry], broken: bool = False) -> None:
        self.months[(page.year, page.month)] = "broken" if broken else "read"
        self.entries[(page.year, page.month)] = list(entries)
        self.writes.append((page.year, page.month))

    def read_months(self) -> set[tuple[int, int]]:
        return {key for key, status in self.months.items() if status == "read"}

    def search(self, query, year, limit, offset) -> tuple[list[CatalogHit], int]:
        return [], 0

    def find_by_number(self, gr_no: GrNumber) -> list[CatalogEntry]:
        return [e for entries in self.entries.values() for e in entries if gr_no.value in e.numbers]

    def status(self, building: bool) -> CatalogStatus:
        total = sum(len(v) for v in self.entries.values())
        known = len(self.months)
        read = len([s for s in self.months.values() if s in ("read", "absent")])
        state = "building" if building else "empty" if total == 0 else "partial" if read < known else "ready"
        return CatalogStatus(total, read, known, state)


class InMemoryDigestRepository(DigestRepository):
    def __init__(self) -> None:
        self.digests: dict[int, CaseDigest] = {}
        self.ai_counts_today = 0

    def get(self, digest_id):
        return self.digests.get(digest_id)

    def find(self, case_id, upload_id):
        return next((d for d in self.digests.values() if d.case_id == case_id and d.upload_id == upload_id), None)

    def add(self, digest):
        digest.id = len(self.digests) + 1
        self.digests[digest.id] = digest
        return digest

    def save(self, digest):
        self.digests[digest.id] = digest

    def list_for_upload(self, upload_id):
        return [d for d in self.digests.values() if d.upload_id == upload_id]

    def count_ai_since(self, since):
        return self.ai_counts_today


class ScriptedWriter(AnswerWriter):
    """Answers every question with the sentences it was given; remembers what it was asked."""

    def __init__(self, sentences=None, error: Exception | None = None):
        self.sentences, self.error, self.requests = sentences or [], error, []

    def write(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return list(self.sentences)


class AlwaysSupported(AnswerChecker):
    def check(self, sentences, sources):
        return [CheckResult(Verdict.SUPPORTED) for _ in sentences]


class InMemoryJobLocks(JobLockRepository):
    """Locks in a dict. `expire(key)` stands in for the time limit running out."""

    def __init__(self) -> None:
        self.held: set[str] = set()
        self.acquired: list[tuple[str, int]] = []

    def acquire(self, key, ttl_seconds):
        if key in self.held:
            return False
        self.held.add(key)
        self.acquired.append((key, ttl_seconds))
        return True

    def release(self, key):
        self.held.discard(key)

    def release_all(self):
        self.held.clear()

    def is_held(self, key):
        return key in self.held

    def expire(self, key):
        self.held.discard(key)
