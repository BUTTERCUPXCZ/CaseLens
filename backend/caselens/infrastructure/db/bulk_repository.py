from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from caselens.application.ports.bulk import BulkRepository
from caselens.domain.digest_v2 import scope_key
from caselens.domain.bulk import BulkBatch, BulkCounts, BulkItem, ItemKind, ItemStatus
from caselens.infrastructure.db.orm_models import BulkBatchModel, BulkItemModel, CaseDigestV2Model


def _item(row: BulkItemModel) -> BulkItem:
    return BulkItem(
        id=row.id, batch_id=row.batch_id, position=row.position, kind=ItemKind(row.kind), label=row.label, gr_no=row.gr_no,
        year=row.year, status=ItemStatus(row.status), message=row.message, case_id=row.case_id, reporter=row.reporter,
        source_url=row.source_url,
    )


def _fill(row: BulkItemModel, item: BulkItem) -> None:
    row.batch_id, row.position, row.kind, row.label = item.batch_id, item.position, item.kind.value, item.label
    row.gr_no, row.year, row.status, row.message, row.case_id = item.gr_no, item.year, item.status.value, item.message, item.case_id
    row.reporter, row.source_url = item.reporter, item.source_url


def _batch(row: BulkBatchModel) -> BulkBatch:
    return BulkBatch(subject_ids=tuple(row.subject_ids or ()), topic_scope=row.topic_scope or "", kind=row.kind or "bulk", id=row.id, created_at=row.created_at)


class SqlBulkRepository(BulkRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_batch(self, batch: BulkBatch) -> BulkBatch:
        row = BulkBatchModel(subject_ids=list(batch.subject_ids), topic_scope=batch.topic_scope, kind=batch.kind)
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        batch.id, batch.created_at = row.id, row.created_at
        if batch.items:
            batch.items = self.add_items(row.id, batch.items)
        return batch

    def add_items(self, batch_id: int, items: Sequence[BulkItem]) -> list[BulkItem]:
        start = (self._session.scalar(select(func.max(BulkItemModel.position)).where(BulkItemModel.batch_id == batch_id)) or 0) + 1
        rows = []
        for offset, item in enumerate(items):
            item.batch_id, item.position = batch_id, start + offset
            row = BulkItemModel()
            _fill(row, item)
            self._session.add(row)
            rows.append((item, row))
        self._session.flush()
        for item, row in rows:
            item.id = row.id
        return [item for item, _ in rows]

    def get_batch(self, batch_id: int) -> BulkBatch | None:
        row = self._session.get(BulkBatchModel, batch_id)
        return _batch(row) if row else None

    def get_item(self, item_id: int) -> BulkItem | None:
        row = self._session.get(BulkItemModel, item_id)
        return _item(row) if row else None

    def save_item(self, item: BulkItem) -> None:
        row = self._session.get(BulkItemModel, item.id)
        _fill(row, item)
        row.updated_at = func.now()
        self._session.flush()

    def _scope_key(self, batch_id: int) -> str:
        return scope_key(self._session.scalar(select(BulkBatchModel.topic_scope).where(BulkBatchModel.id == batch_id)))

    def counts(self, batch_id: int) -> BulkCounts:
        def n(*conditions):
            return func.count().filter(*conditions) if conditions else func.count()

        status = BulkItemModel.status
        found = status == ItemStatus.FOUND.value
        row = self._session.execute(
            select(
                n(), n(status == ItemStatus.QUEUED.value), n(found), n(status == ItemStatus.DUPLICATE.value),
                n(status == ItemStatus.NOT_FOUND.value), n(status == ItemStatus.UNREADABLE.value), n(status == ItemStatus.FAILED.value),
                n(found, CaseDigestV2Model.state == "ready"), n(found, CaseDigestV2Model.state == "pending"), n(found, CaseDigestV2Model.state == "failed"),
            )
            .select_from(BulkItemModel)
            .outerjoin(
                CaseDigestV2Model, (CaseDigestV2Model.case_id == BulkItemModel.case_id) & (CaseDigestV2Model.scope_key == self._scope_key(batch_id))
            )
            .where(BulkItemModel.batch_id == batch_id)
        ).one()
        return BulkCounts(*row)

    def items(self, batch_id: int, status: ItemStatus | None, limit: int, offset: int) -> tuple[list[BulkItem], int]:
        conditions = [BulkItemModel.batch_id == batch_id]
        if status is not None:
            conditions.append(BulkItemModel.status == status.value)
        total = self._session.scalar(select(func.count()).select_from(BulkItemModel).where(*conditions)) or 0
        rows = self._session.scalars(select(BulkItemModel).where(*conditions).order_by(BulkItemModel.position).limit(limit).offset(offset))
        return [_item(r) for r in rows], total

    def recent(self, limit: int, offset: int = 0) -> list[BulkBatch]:
        rows = self._session.scalars(select(BulkBatchModel).order_by(BulkBatchModel.id.desc()).limit(limit).offset(offset))
        return [_batch(r) for r in rows]

    def reporter_for(self, batch_id: int, case_id: int) -> str | None:
        return self._session.scalar(
            select(BulkItemModel.reporter)
            .where(BulkItemModel.batch_id == batch_id, BulkItemModel.case_id == case_id, BulkItemModel.reporter.is_not(None))
            .order_by(BulkItemModel.position)
            .limit(1)
        )

    def delete_batch(self, batch_id: int) -> bool:
        row = self._session.get(BulkBatchModel, batch_id)
        if row is None:
            return False
        self._session.delete(row)  # its items and questions go with it (ON DELETE CASCADE); cases and digests stay
        self._session.flush()
        return True

    def earlier_item_for_case(self, batch_id: int, case_id: int, before_position: int) -> BulkItem | None:
        row = self._session.scalars(
            select(BulkItemModel)
            .where(BulkItemModel.batch_id == batch_id, BulkItemModel.case_id == case_id, BulkItemModel.position < before_position,
                   BulkItemModel.status == ItemStatus.FOUND.value)
            .order_by(BulkItemModel.position)
            .limit(1)
        ).first()
        return _item(row) if row else None

    def main_case_ids(self, batch_id: int) -> list[int]:
        rows = self._session.execute(
            select(BulkItemModel.case_id, func.min(BulkItemModel.position).label("first"))
            .where(BulkItemModel.batch_id == batch_id, BulkItemModel.status == ItemStatus.FOUND.value, BulkItemModel.case_id.is_not(None))
            .group_by(BulkItemModel.case_id)
            .order_by("first")
        )
        return [r.case_id for r in rows]

    def ids_with_status(self, status: ItemStatus, limit: int) -> list[int]:
        return list(self._session.scalars(select(BulkItemModel.id).where(BulkItemModel.status == status.value).order_by(BulkItemModel.id).limit(limit)))
