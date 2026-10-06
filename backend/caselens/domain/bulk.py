"""Bulk upload: many cases at once, each file or G.R. number being ONE main case.

An item is one thing the student gave (a typed G.R. number, or a PDF/Word file of a decision). It ends in a main case of the library,
or in a plain reason why not. Cases a decision merely cites are never items."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ItemStatus(str, Enum):
    QUEUED = "queued"  # waiting its turn (Lawphil is read at one page a second)
    FOUND = "found"  # the case is in the library
    DUPLICATE = "duplicate"  # the same case as an earlier item: shown once
    NOT_FOUND = "not_found"  # the number is not on Lawphil's list (or is older than the list)
    UNREADABLE = "unreadable"  # no G.R. number could be read from the file, or the text is not a G.R. number
    FAILED = "failed"  # Lawphil did not answer; asking again retries


class ItemKind(str, Enum):
    GR_NUMBER = "gr_number"  # typed or pasted
    FILE = "file"  # a PDF or Word file of a decision


@dataclass
class BulkItem:
    batch_id: int
    position: int
    kind: ItemKind
    label: str  # what the student gave: "88211" or "Marcos v Manglapus.pdf"
    gr_no: str | None = None  # the main G.R. number read from it
    year: int | None = None  # a year hint ("88211 (1989)"), for a number the list does not know
    status: ItemStatus = ItemStatus.QUEUED
    message: str | None = None
    case_id: int | None = None  # the MAIN case it ended in
    id: int | None = None
    reporter: str | None = None  # the reporter citation the file printed ("177 SCRA 668"), shown on the digest's citation line
    # The exact Lawphil page the student picked (Individual): a decision and its later Resolution share the number and the year,
    # so the page decides which one is opened, not the number.
    source_url: str | None = None


UPLOAD_KINDS = ("individual", "bulk")


@dataclass
class BulkBatch:
    subject_ids: tuple[int, ...] = ()  # the tags chosen once for the whole upload (may be none)
    topic_scope: str = ""  # narrows every digest of this upload to one doctrine or issue ("" = the standard digest)
    kind: str = "bulk"  # "individual": one case, opened for its full text; "bulk": many cases
    id: int | None = None
    created_at: datetime | None = None
    items: list[BulkItem] = field(default_factory=list)


@dataclass(frozen=True)
class BulkCounts:
    total: int = 0
    queued: int = 0
    found: int = 0
    duplicate: int = 0
    not_found: int = 0
    unreadable: int = 0
    failed: int = 0
    digests_ready: int = 0  # of the found cases
    digests_pending: int = 0
    digests_failed: int = 0

    @property
    def finished(self) -> bool:
        return self.total > 0 and self.queued == 0
