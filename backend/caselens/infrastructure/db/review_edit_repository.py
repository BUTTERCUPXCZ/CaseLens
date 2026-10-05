from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from caselens.application.ports.review_edits import ReviewEditRepository
from caselens.domain.digest_v2 import Section
from caselens.infrastructure.db.orm_models import ReviewDigestEditModel


class SqlReviewEditRepository(ReviewEditRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def for_digest(self, batch_id: int, digest_id: int) -> dict[Section, str]:
        rows = self._session.execute(
            select(ReviewDigestEditModel.section, ReviewDigestEditModel.text).where(
                ReviewDigestEditModel.batch_id == batch_id, ReviewDigestEditModel.digest_id == digest_id
            )
        )
        return {Section(section): text for section, text in rows if section in Section._value2member_map_}

    def save(self, batch_id: int, digest_id: int, section: Section, text: str) -> None:
        values = {"batch_id": batch_id, "digest_id": digest_id, "section": section.value, "text": text}
        self._session.execute(
            pg_insert(ReviewDigestEditModel)
            .values(values)
            .on_conflict_do_update(constraint="uq_review_digest_edits_section", set_={"text": text, "updated_at": func.now()})
        )
        self._session.flush()

    def remove(self, batch_id: int, digest_id: int, section: Section) -> None:
        self._session.execute(
            delete(ReviewDigestEditModel).where(
                ReviewDigestEditModel.batch_id == batch_id, ReviewDigestEditModel.digest_id == digest_id, ReviewDigestEditModel.section == section.value
            )
        )
        self._session.flush()
