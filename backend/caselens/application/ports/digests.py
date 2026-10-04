from abc import ABC, abstractmethod
from datetime import datetime

from caselens.domain.case_digest import CaseDigest


class DigestRepository(ABC):
    @abstractmethod
    def get(self, digest_id: int) -> CaseDigest | None: ...

    @abstractmethod
    def find(self, case_id: int, upload_id: int | None) -> CaseDigest | None:
        """The digest of this case within this upload (or the stand-alone one when upload_id is None)."""

    @abstractmethod
    def add(self, digest: CaseDigest) -> CaseDigest:
        """Store a new digest and return it with its id."""

    @abstractmethod
    def save(self, digest: CaseDigest) -> None: ...

    @abstractmethod
    def list_for_upload(self, upload_id: int) -> list[CaseDigest]: ...

    @abstractmethod
    def count_ai_since(self, since: datetime) -> int:
        """How many digests had AI answers written since this time (the daily cost guard)."""
