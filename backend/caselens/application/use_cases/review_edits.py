from caselens.application.ports.bulk import BulkRepository
from caselens.application.ports.digests import CaseDigestRepository
from caselens.application.ports.repositories import UnitOfWork
from caselens.application.ports.review_edits import ReviewEditRepository
from caselens.domain.digest_v2 import Section
from caselens.domain.errors import CaseNotFoundError, DigestNotFoundError, DomainError
from caselens.domain.section_edits import MAX_SECTION_TEXT


class EditDigestSection:
    """The student rewrites one section of a digest in their review, or puts back the AI's text. The shared digest is never changed."""

    def __init__(self, bulk: BulkRepository, digests: CaseDigestRepository, edits: ReviewEditRepository, uow: UnitOfWork) -> None:
        self._bulk = bulk
        self._digests = digests
        self._edits = edits
        self._uow = uow

    def save(self, batch_id: int, digest_id: int, section: Section, text: str) -> None:
        self._check(batch_id, digest_id)
        if len(text) > MAX_SECTION_TEXT:
            raise DomainError(f"Keep a section under {MAX_SECTION_TEXT:,} characters.")
        self._edits.save(batch_id, digest_id, section, text.strip())
        self._uow.commit()

    def put_back(self, batch_id: int, digest_id: int, section: Section) -> None:
        self._check(batch_id, digest_id)
        self._edits.remove(batch_id, digest_id, section)
        self._uow.commit()

    def _check(self, batch_id: int, digest_id: int) -> None:
        if self._bulk.get_batch(batch_id) is None:
            raise CaseNotFoundError(f"Review {batch_id} does not exist.")
        if self._digests.get_by_id(digest_id) is None:
            raise DigestNotFoundError(f"Case digest {digest_id} does not exist.")
