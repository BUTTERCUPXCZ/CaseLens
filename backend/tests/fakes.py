"""In-memory stand-ins for ports. Using them proves the use cases only depend on the
port (Liskov): the same code runs against SQL or a dict."""
from datetime import datetime

from caselens.application.ports.ai import AnswerChecker, AnswerWriter, DigestWriter, PassageChecker, PassagePicker
from caselens.application.ports.bulk import BulkRepository
from caselens.application.ports.digests import CaseDigestRepository, DigestRepository
from caselens.domain.bulk import BulkCounts, ItemStatus
from caselens.application.ports.gateways import CaseFetcher, CaseLocator, JobQueue
from caselens.application.ports.locks import JobLockRepository
from caselens.application.ports.repositories import (
    SubjectRepository,
    CaseRepository,
    MonthIndexRepository,
    UnitOfWork,
    UploadRepository,
)
from caselens.domain.case_digest import CaseDigest
from caselens.domain.digest import CheckResult, Verdict
from caselens.domain.subjects import DEFAULT_SUBJECTS, Subject, SubjectCount
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
        self.subject_names: dict[int, str] = {}
        self.tags: dict[int, dict[int, str]] = {}  # case id -> {subject id: source}

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
                           c.division, c.disposition, c.source_url, c.subjects, c.main_case_id, c.all_numbers)

    def find_overlapping(self, numbers):
        wanted = set(numbers)
        return [self._summary(c) for c in self.cases.values() if wanted & set(c.all_numbers)]

    def set_main_case(self, case_ids, main_case_id):
        for i in case_ids:
            if i != main_case_id:
                self.cases[i].main_case_id = main_case_id
        if main_case_id is not None:
            self.cases[main_case_id].main_case_id = None

    def add_subjects(self, case_id, subject_ids, source):
        tags = self.tags.setdefault(case_id, {})
        for i in subject_ids:
            tags.setdefault(i, source)
        self._show_tags(case_id)

    def set_subjects(self, case_id, subject_ids, source):
        self.tags[case_id] = {i: source for i in subject_ids}
        self._show_tags(case_id)

    def _show_tags(self, case_id):
        order = list(self.subject_names)
        ids = sorted(self.tags.get(case_id, {}), key=lambda i: order.index(i) if i in order else i)
        self.cases[case_id].subjects = tuple(Subject(i, self.subject_names.get(i, f"Subject {i}")) for i in ids)

    def subject_counts(self):
        counts: dict = {}
        for c in self.cases.values():
            if c.main_case_id is None:
                for i in self.tags.get(c.id, {}) or [None]:
                    counts[i] = counts.get(i, 0) + 1
        return [SubjectCount(i, name, counts.get(i, 0)) for i, name in self.subject_names.items()] + [SubjectCount(None, "No subject yet", counts.get(None, 0))]

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

    def search(self, query: str | None, limit: int, offset: int, subject_id: int | None = None, no_subject: bool = False) -> tuple[list[CaseSummary], int]:
        def matches(case: Case) -> bool:
            if case.main_case_id is not None:
                return False
            tags = self.tags.get(case.id, {})
            if subject_id is not None and subject_id not in tags:
                return False
            if no_subject and tags:
                return False
            if not query:
                return True
            return query.lower() in (case.title or "").lower() or str(case.gr_no).startswith(query)

        found = [c for c in self.cases.values() if matches(c)]
        found.sort(key=lambda c: (c.decision_date is not None, c.decision_date, c.id), reverse=True)
        summaries = [self._summary(c) for c in found]
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

    def delete(self, upload_id: int) -> bool:
        return self.uploads.pop(upload_id, None) is not None

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
        self.case_digests: list[int] = []  # digest ids
        self.case_questions: list[int] = []
        self.bulk_items: list[int] = []
        self.catalog_builds: list[int] = []
        self.catalog_refreshes = 0
        self.catalog_refresh_locked = False
        self.catalog_build_running = False

    def enqueue_build_digest(self, digest_id: int, keys: list[str] | None = None) -> None:
        self.digest_builds.append((digest_id, keys))

    def enqueue_bulk_item(self, item_id: int) -> None:
        self.bulk_items.append(item_id)

    def enqueue_case_digest(self, digest_id: int) -> None:
        self.case_digests.append(digest_id)

    def enqueue_case_question(self, question_id: int) -> None:
        self.case_questions.append(question_id)

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
        self.saved_urls: set[str] = set()

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

    def unsaved(self, first_year, last_year, after_id, limit):
        urls = dict.fromkeys(e.source_url for (year, _), entries in self.entries.items() for e in entries if first_year <= year <= last_year)
        return [(i, url) for i, url in enumerate(urls, start=1) if i > after_id and url not in self.saved_urls][:limit]

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


class ScriptedPicker(PassagePicker):
    """Points at the paragraphs it was told to (first, last) per key; remembers what it was offered."""

    def __init__(self, picks=None, error: Exception | None = None):
        self.picks, self.error, self.requests = picks or {}, error, []

    def pick(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return {key: self.picks.get(key) for key in request.keys}


class ScriptedPassageChecker(PassageChecker):
    """Gives each part the verdict it was told to (default: supported); remembers the text it was shown."""

    def __init__(self, verdicts=None, silent=False):
        self.verdicts, self.silent, self.seen = verdicts or {}, silent, []

    def check(self, passages):
        self.seen.append(dict(passages))
        if self.silent:
            return {}
        return {key: CheckResult(self.verdicts.get(key, Verdict.SUPPORTED), "scripted") for key in passages}


class ScriptedDigestWriter(DigestWriter):
    """Returns the draft it was given; `repairs` maps the position of a failed sentence to its rewrite."""

    def __init__(self, draft, repairs=None):
        self.draft, self.repairs, self.repair_calls, self.requests = draft, repairs or {}, [], []
        self.repair_requests = []  # what each repair was given to work from (only the passages near the failed sentences)

    def write(self, request):
        self.requests.append(request)
        return self.draft

    def repair(self, request, failed):
        self.repair_calls.append(failed)
        self.repair_requests.append(request)
        return {n: sentence for n, sentence in self.repairs.items() if n < len(failed)}


class VerdictChecker(AnswerChecker):
    """Judges each sentence by a rule: `unsupported` is the set of sentence texts it will not support."""

    def __init__(self, unsupported=()):
        self.unsupported, self.seen = set(unsupported), []

    def check(self, sentences, sources):
        self.seen.append([s.text for s in sentences])
        return [CheckResult(Verdict.NOT_SUPPORTED if s.text in self.unsupported else Verdict.SUPPORTED, "scripted") for s in sentences]


class InMemorySubjectRepository(SubjectRepository):
    def __init__(self, names=DEFAULT_SUBJECTS):
        self.subjects = [Subject(i, name) for i, name in enumerate(names, start=1)]

    def list(self):
        return list(self.subjects)

    def get(self, subject_id):
        return next((s for s in self.subjects if s.id == subject_id), None)


class InMemoryCaseDigestRepository(CaseDigestRepository):
    def __init__(self):
        self.rows = {}  # (case id, scope key) -> digest
        self.started = []  # the creation times, for the monthly limit

    @property
    def by_case(self):
        """The standard digests (no scope), by case id."""
        return {case_id: d for (case_id, key), d in self.rows.items() if key == ""}

    def get(self, case_id, scope_key=""):
        return self.rows.get((case_id, scope_key))

    def get_by_id(self, digest_id):
        return next((d for d in self.rows.values() if d.id == digest_id), None)

    def save(self, digest):
        key = (digest.case_id, digest.scope_key)
        if key not in self.rows:
            digest.id = len(self.rows) + 1
            self.started.append(getattr(digest, "started_at", None) or datetime(2026, 10, 5))
        self.rows[key] = digest
        return digest

    def count_started_since(self, since):
        return sum(1 for t in self.started if t.replace(tzinfo=since.tzinfo) >= since)  # the fake keeps naive times; the real month start is UTC

    def ready_case_ids(self, case_ids, scope_key=""):
        return {i for i, state in self.states(case_ids, scope_key).items() if state == "ready"}

    def states(self, case_ids, scope_key=""):
        return {i: self.rows[(i, scope_key)].state.value for i in case_ids if (i, scope_key) in self.rows}


class InMemoryBulkRepository(BulkRepository):
    def __init__(self):
        self.batches, self.items_by_id, self._next_batch, self._next_item = {}, {}, 1, 1

    def add_batch(self, batch):
        batch.id, batch.created_at = self._next_batch, datetime(2026, 10, 5)
        self._next_batch += 1
        items, batch.items = batch.items, []
        self.batches[batch.id] = batch
        if items:
            batch.items = self.add_items(batch.id, items)
        return batch

    def add_items(self, batch_id, items):
        start = 1 + max([i.position for i in self.items_by_id.values() if i.batch_id == batch_id], default=0)
        for offset, item in enumerate(items):
            item.batch_id, item.position, item.id = batch_id, start + offset, self._next_item
            self._next_item += 1
            self.items_by_id[item.id] = item
        return list(items)

    def get_batch(self, batch_id):
        return self.batches.get(batch_id)

    def get_item(self, item_id):
        return self.items_by_id.get(item_id)

    def save_item(self, item):
        self.items_by_id[item.id] = item

    def counts(self, batch_id):
        mine = [i for i in self.items_by_id.values() if i.batch_id == batch_id]
        n = lambda status: sum(1 for i in mine if i.status is status)  # noqa: E731
        return BulkCounts(len(mine), n(ItemStatus.QUEUED), n(ItemStatus.FOUND), n(ItemStatus.DUPLICATE), n(ItemStatus.NOT_FOUND), n(ItemStatus.UNREADABLE), n(ItemStatus.FAILED))

    def items(self, batch_id, status, limit, offset):
        mine = sorted((i for i in self.items_by_id.values() if i.batch_id == batch_id and (status is None or i.status is status)), key=lambda i: i.position)
        return mine[offset : offset + limit], len(mine)

    def recent(self, limit, offset=0):
        return sorted(self.batches.values(), key=lambda b: -b.id)[offset : offset + limit]

    def reporter_for(self, batch_id, case_id):
        return next((i.reporter for i in sorted(self.items_by_id.values(), key=lambda i: i.position) if i.batch_id == batch_id and i.case_id == case_id and i.reporter), None)

    def delete_batch(self, batch_id):
        if self.batches.pop(batch_id, None) is None:
            return False
        self.items_by_id = {k: v for k, v in self.items_by_id.items() if v.batch_id != batch_id}
        return True

    def earlier_item_for_case(self, batch_id, case_id, before_position):
        found = [i for i in self.items_by_id.values() if i.batch_id == batch_id and i.case_id == case_id and i.position < before_position and i.status is ItemStatus.FOUND]
        return min(found, key=lambda i: i.position) if found else None

    def main_case_ids(self, batch_id):
        found = sorted((i for i in self.items_by_id.values() if i.batch_id == batch_id and i.status is ItemStatus.FOUND and i.case_id is not None), key=lambda i: i.position)
        return list(dict.fromkeys(i.case_id for i in found))

    def ids_with_status(self, status, limit):
        return [i.id for i in self.items_by_id.values() if i.status is status][:limit]


from caselens.application.ports.questions import CaseQuestionRepository  # noqa: E402
from caselens.domain.case_question import CaseQuestion  # noqa: E402


class InMemoryCaseQuestionRepository(CaseQuestionRepository):
    def __init__(self):
        self.rows: dict[int, "CaseQuestion"] = {}
        self.asked_at: list[datetime] = []

    def add(self, question):
        question.id = len(self.rows) + 1
        question.created_at = datetime(2026, 10, 5, 9)
        self.rows[question.id] = question
        self.asked_at.append(question.created_at)
        return question

    def get(self, question_id):
        return self.rows.get(question_id)

    def save(self, question):
        self.rows[question.id] = question

    def list_for(self, case_id, batch_id):
        return [q for q in self.rows.values() if q.case_id == case_id and q.batch_id == batch_id]

    def count_since(self, since):
        return sum(1 for t in self.asked_at if t.replace(tzinfo=since.tzinfo) >= since)


from caselens.application.ports.review_edits import ReviewEditRepository  # noqa: E402


class InMemoryReviewEditRepository(ReviewEditRepository):
    def __init__(self):
        self.rows = {}  # (batch id, digest id, section) -> text

    def for_digest(self, batch_id, digest_id):
        return {section: text for (b, d, section), text in self.rows.items() if (b, d) == (batch_id, digest_id)}

    def save(self, batch_id, digest_id, section, text):
        self.rows[(batch_id, digest_id, section)] = text

    def remove(self, batch_id, digest_id, section):
        self.rows.pop((batch_id, digest_id, section), None)
