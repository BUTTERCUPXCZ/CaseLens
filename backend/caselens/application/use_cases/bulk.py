import logging
from collections.abc import Sequence
from dataclasses import dataclass

from caselens.application.ports.bulk import BulkRepository
from caselens.application.ports.gateways import JobQueue, UploadedFileReader
from caselens.application.ports.repositories import CaseRepository, SubjectRepository, UnitOfWork
from caselens.application.use_cases.case_digest_v2 import RequestCaseDigestV2
from caselens.application.use_cases.fetch_case_by_gr_number import FetchCaseByGrNumber
from caselens.domain.bulk import UPLOAD_KINDS, BulkBatch, BulkCounts, BulkItem, ItemKind, ItemStatus
from caselens.application.use_cases.ingest_case import IngestCase
from caselens.domain.errors import CaseNotFoundError, CaseParseError, DomainError, InvalidSourceUrlError, SourceUnavailableError
from caselens.domain.services.case_names import short_case_name
from caselens.domain.services.gr_list_parser import GrListParser
from caselens.domain.services.main_case_identifier import MainCaseIdentifier, ReviewerCaseFinder
from caselens.domain.digest_v2 import clean_scope
from caselens.domain.subjects import SOURCE_BATCH
from caselens.domain.value_objects import GrNumber

logger = logging.getLogger(__name__)

MAX_FILES_PER_REQUEST = 10
_NOT_A_NUMBER = "This is not a G.R. number, so it was skipped."
_NO_CASE_IN_FILE = (
    "We could not find a case in this file: no G.R. number at the top of a decision, and no case under a “Digest” heading "
    "(like “Digest 1: Facts and Doctrine” followed by “Review Center v Ermita, 538 SCRA 428, GR no 180046”)."
)
_ONE_CASE = "Individual is for one case. This has more than one: use Bulk for several cases."
_LAWPHIL_DOWN = "Lawphil did not answer, or its page could not be read. Press Retry to try again."
_NOT_A_LAWPHIL_PAGE = "That is not a Lawphil case page, so it was not opened."


def _not_found(item: BulkItem) -> str:
    if item.year is not None:
        return f"G.R. No. {item.gr_no} was not found on Lawphil near {item.year}."
    return (
        f"G.R. No. {item.gr_no} is not on Lawphil's list of decisions, which starts in 1987. "
        f"If it is older, write it with its year, like {item.gr_no} (1969), and try again."
    )


@dataclass(frozen=True)
class BulkView:
    batch: BulkBatch
    counts: BulkCounts
    labels: tuple[str, ...] = ()  # the first few files or numbers given, to name the upload in a list
    cases: tuple[tuple[str, str], ...] = ()  # the first few main cases it gave: (case name, G.R. number)
    case_total: int = 0  # how many main cases it gave in all


class StartBulkBatch:
    """Starts a bulk upload with the G.R. numbers pasted so far (possibly none: files follow). One number is one item; each item will end in ONE main case."""

    def __init__(self, parser: GrListParser, subjects: SubjectRepository, bulk: BulkRepository, jobs: JobQueue, uow: UnitOfWork) -> None:
        self._parser = parser
        self._subjects = subjects
        self._bulk = bulk
        self._jobs = jobs
        self._uow = uow

    def execute(
        self, text: str, subject_ids: Sequence[int] = (), topic_scope: str = "", kind: str = "bulk", source_url: str | None = None
    ) -> BulkBatch:
        """`source_url`: the exact Lawphil page the student picked (Individual only). It decides which page is opened, since a decision
        and its later Resolution can share the number and even the year."""
        if kind not in UPLOAD_KINDS:
            raise DomainError(f"Unknown kind of upload: {kind}.")
        if source_url is not None and kind != "individual":
            raise DomainError("A picked Lawphil page is only for Individual (one case).")
        tags = tuple(dict.fromkeys(subject_ids))
        for subject_id in tags:
            if self._subjects.get(subject_id) is None:
                raise DomainError(f"Subject {subject_id} does not exist.")
        items = [
            BulkItem(0, 0, ItemKind.GR_NUMBER, entry.raw, entry.gr_no.value, entry.year)
            if entry.gr_no is not None
            else BulkItem(0, 0, ItemKind.GR_NUMBER, entry.raw, None, None, ItemStatus.UNREADABLE, _NOT_A_NUMBER)
            for entry in self._parser.parse(text)
        ]
        if kind == "individual" and len(items) > 1:
            raise DomainError(_ONE_CASE)
        if source_url is not None:
            if len(items) != 1 or items[0].gr_no is None:
                raise DomainError("Give the G.R. number of the Lawphil page you picked.")
            items[0].source_url = source_url
        batch = self._bulk.add_batch(BulkBatch(subject_ids=tags, topic_scope=clean_scope(topic_scope), kind=kind, items=items))
        self._uow.commit()  # commit first so the worker sees the items
        for item in batch.items:
            if item.status is ItemStatus.QUEUED:
                self._jobs.enqueue_bulk_item(item.id)
        return batch


class AddBulkFiles:
    """Adds decision files (PDF or Word) to a batch. A file is ONE main case: only its caption is read for the G.R. number, so the cases the
    decision cites never become items. A file with no readable number is kept as an item that says so."""

    def __init__(
        self, reader: UploadedFileReader, identifier: MainCaseIdentifier, bulk: BulkRepository, jobs: JobQueue, uow: UnitOfWork, reviewer: ReviewerCaseFinder | None = None
    ) -> None:
        self._reader = reader
        self._identifier = identifier
        self._reviewer = reviewer or ReviewerCaseFinder()
        self._bulk = bulk
        self._jobs = jobs
        self._uow = uow

    def execute(self, batch_id: int, files: Sequence[tuple[str, bytes]]) -> list[BulkItem]:
        batch = self._bulk.get_batch(batch_id)
        if batch is None:
            raise CaseNotFoundError(f"Bulk upload {batch_id} does not exist.")
        if len(files) > MAX_FILES_PER_REQUEST:
            raise DomainError(f"Send at most {MAX_FILES_PER_REQUEST} files at a time.")
        items = [item for name, data in files for item in self._items(name, data)]
        if batch.kind == "individual" and self._bulk.counts(batch_id).total + len(items) > 1:
            raise DomainError(_ONE_CASE)
        stored = self._bulk.add_items(batch_id, items)
        self._uow.commit()
        for item in stored:
            if item.status is ItemStatus.QUEUED:
                self._jobs.enqueue_bulk_item(item.id)
        return stored

    def _items(self, name: str, data: bytes) -> list[BulkItem]:
        """A decision is one case (read from its caption). A student's reviewer is the cases under its "Digest N:" boxes, each once."""
        try:
            text = self._reader.read(name, data)
        except DomainError as exc:
            return [BulkItem(0, 0, ItemKind.FILE, name, None, None, ItemStatus.UNREADABLE, str(exc))]
        found = self._identifier.identify(text)
        if found.main is not None:
            return [BulkItem(0, 0, ItemKind.FILE, name, found.main.value, found.year, reporter=found.reporter)]
        boxed = self._reviewer.find(text)
        if boxed:
            # the year the student wrote is not passed on: a wrong year must not send the search to the wrong month (the number decides)
            return [BulkItem(0, 0, ItemKind.FILE, f"{name}: {case.title}", case.gr_no.value, None, reporter=case.reporter) for case in boxed]
        return [BulkItem(0, 0, ItemKind.FILE, name, None, None, ItemStatus.UNREADABLE, _NO_CASE_IN_FILE)]


class ResolveBulkItem:
    """The background step for one item: get the official decision from Lawphil, find its MAIN case, add the upload's tags, and ask for
    its digest (for the upload's topic scope). Safe to run twice (a finished item is left alone)."""

    def __init__(
        self,
        bulk: BulkRepository,
        fetch: FetchCaseByGrNumber,
        cases: CaseRepository,
        digests: RequestCaseDigestV2,
        uow: UnitOfWork,
        ingest: IngestCase | None = None,
    ) -> None:
        self._bulk = bulk
        self._fetch = fetch
        self._cases = cases
        self._digests = digests
        self._uow = uow
        self._ingest = ingest

    def execute(self, item_id: int) -> BulkItem:
        item = self._bulk.get_item(item_id)
        if item is None or item.status is not ItemStatus.QUEUED or item.gr_no is None:
            return item  # type: ignore[return-value]  # already settled (a message delivered twice)
        batch = self._bulk.get_batch(item.batch_id)
        number = GrNumber(item.gr_no)
        picked = item.source_url if self._ingest is not None else None  # the exact page the student chose, not "the newest page for the number"
        existed = (self._cases.get_by_source_url(picked) if picked else self._fetch.find_stored(number)) is not None
        try:
            case = self._ingest.execute(picked) if picked and self._ingest else self._fetch.execute(number, item.year)
        except CaseNotFoundError:
            return self._settle(item, ItemStatus.NOT_FOUND, _not_found(item))
        except InvalidSourceUrlError:
            return self._settle(item, ItemStatus.UNREADABLE, _NOT_A_LAWPHIL_PAGE)
        except (SourceUnavailableError, CaseParseError) as exc:
            logger.warning("bulk item %s (G.R. No. %s): %s", item.id, item.gr_no, exc)
            return self._settle(item, ItemStatus.FAILED, _LAWPHIL_DOWN)

        main_id = case.main_case_id or case.id
        item.case_id = main_id
        earlier = self._bulk.earlier_item_for_case(item.batch_id, main_id, item.position)
        if earlier is not None:
            return self._settle(item, ItemStatus.DUPLICATE, f"The same case as “{earlier.label}”: it is shown once.")

        if batch is not None and batch.subject_ids:
            self._cases.add_subjects(main_id, batch.subject_ids, SOURCE_BATCH)  # adds the upload's tags; tags the case already has stay
        self._digests.execute(main_id, batch.topic_scope if batch is not None else "")  # queues the digest for this scope once
        return self._settle(item, ItemStatus.FOUND, "Already in your library." if existed else None)

    def _settle(self, item: BulkItem, status: ItemStatus, message: str | None) -> BulkItem:
        item.status, item.message = status, message
        self._bulk.save_item(item)
        self._uow.commit()
        return item


_CASES_SHOWN = 3


class GetBulkBatch:
    def __init__(self, bulk: BulkRepository, cases: CaseRepository | None = None) -> None:
        self._bulk = bulk
        self._cases = cases

    def execute(self, batch_id: int) -> BulkView:
        batch = self._bulk.get_batch(batch_id)
        if batch is None:
            raise CaseNotFoundError(f"Bulk upload {batch_id} does not exist.")
        return self._view(batch)

    def _view(self, batch: BulkBatch) -> BulkView:
        assert batch.id is not None
        first, _ = self._bulk.items(batch.id, None, 3, 0)
        named: tuple[tuple[str, str], ...] = ()
        main_ids = self._bulk.main_case_ids(batch.id)
        if self._cases is not None and main_ids:
            known = self._cases.summaries(main_ids[:_CASES_SHOWN])
            named = tuple((short_case_name(known[i].title), str(known[i].gr_no)) for i in main_ids[:_CASES_SHOWN] if i in known)
        return BulkView(batch, self._bulk.counts(batch.id), tuple(i.label for i in first), named, len(main_ids))

    def items(self, batch_id: int, status: ItemStatus | None, limit: int, offset: int) -> tuple[list[BulkItem], int]:
        if self._bulk.get_batch(batch_id) is None:
            raise CaseNotFoundError(f"Bulk upload {batch_id} does not exist.")
        return self._bulk.items(batch_id, status, limit, offset)

    def recent(self, limit: int, offset: int = 0) -> list[BulkView]:
        return [self._view(b) for b in self._bulk.recent(limit, offset)]

    def delete(self, batch_id: int, uow: UnitOfWork) -> None:
        if not self._bulk.delete_batch(batch_id):
            raise CaseNotFoundError(f"Bulk upload {batch_id} does not exist.")
        uow.commit()


class RetryBulkBatch:
    """Queue the items Lawphil could not answer for, again."""

    def __init__(self, bulk: BulkRepository, jobs: JobQueue, uow: UnitOfWork) -> None:
        self._bulk = bulk
        self._jobs = jobs
        self._uow = uow

    def execute(self, batch_id: int) -> int:
        if self._bulk.get_batch(batch_id) is None:
            raise CaseNotFoundError(f"Bulk upload {batch_id} does not exist.")
        failed, _ = self._bulk.items(batch_id, ItemStatus.FAILED, 5000, 0)  # a snapshot: an item that fails again waits for the next press
        for item in failed:
            item.status, item.message = ItemStatus.QUEUED, None
            self._bulk.save_item(item)
        self._uow.commit()
        for item in failed:
            self._jobs.enqueue_bulk_item(item.id)
        return len(failed)
