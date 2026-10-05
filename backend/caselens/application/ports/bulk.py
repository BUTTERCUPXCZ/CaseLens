from abc import ABC, abstractmethod
from collections.abc import Sequence

from caselens.domain.bulk import BulkBatch, BulkCounts, BulkItem, ItemStatus


class BulkRepository(ABC):
    @abstractmethod
    def add_batch(self, batch: BulkBatch) -> BulkBatch:
        """Store a new batch (with any items it has); returns it with ids and the creation time filled."""

    @abstractmethod
    def add_items(self, batch_id: int, items: Sequence[BulkItem]) -> list[BulkItem]:
        """Append items to a batch, numbering them after the ones already there; returns them with ids."""

    @abstractmethod
    def get_batch(self, batch_id: int) -> BulkBatch | None:
        """The batch without its items (a batch can have thousands)."""

    @abstractmethod
    def get_item(self, item_id: int) -> BulkItem | None: ...

    @abstractmethod
    def save_item(self, item: BulkItem) -> None: ...

    @abstractmethod
    def counts(self, batch_id: int) -> BulkCounts:
        """How each item ended so far, and how the digests of the found cases are coming along."""

    @abstractmethod
    def items(self, batch_id: int, status: ItemStatus | None, limit: int, offset: int) -> tuple[list[BulkItem], int]:
        """A page of a batch's items in the order they were given, optionally one status only, plus the total."""

    @abstractmethod
    def recent(self, limit: int, offset: int = 0) -> list[BulkBatch]:
        """The latest batches, newest first (without items)."""

    @abstractmethod
    def reporter_for(self, batch_id: int, case_id: int) -> str | None:
        """The reporter citation ("177 SCRA 668") a file of this batch printed for this case, if any."""

    @abstractmethod
    def delete_batch(self, batch_id: int) -> bool:
        """Remove a batch with its items and the questions asked in it; its cases and digests stay. False if there was none."""

    @abstractmethod
    def earlier_item_for_case(self, batch_id: int, case_id: int, before_position: int) -> BulkItem | None:
        """The first item of this batch before `before_position` that already ended in this main case."""

    @abstractmethod
    def main_case_ids(self, batch_id: int) -> list[int]:
        """The main cases this batch ended in, each once, in the order the items were given."""

    @abstractmethod
    def ids_with_status(self, status: ItemStatus, limit: int) -> list[int]:
        """Item ids still in this status, oldest first (to pick up again after a restart)."""
