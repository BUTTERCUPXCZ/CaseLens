from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from caselens.domain.case_digest import CaseDigest
from caselens.domain.digest_v2 import CaseDigestV2


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


class CaseDigestRepository(ABC):
    """The case digests (the client's format): one per main case and topic scope ("" = the standard digest)."""

    @abstractmethod
    def get(self, case_id: int, scope_key: str = "") -> CaseDigestV2 | None: ...

    @abstractmethod
    def get_by_id(self, digest_id: int) -> CaseDigestV2 | None: ...

    @abstractmethod
    def save(self, digest: CaseDigestV2) -> CaseDigestV2:
        """Insert the digest, or replace the stored one of the same case and scope."""

    @abstractmethod
    def count_started_since(self, since: datetime) -> int:
        """How many digests were started since this moment (for the monthly limit on AI work)."""

    @abstractmethod
    def ready_case_ids(self, case_ids: Sequence[int], scope_key: str = "") -> set[int]:
        """Which of these cases already have a finished digest for this scope."""

    @abstractmethod
    def states(self, case_ids: Sequence[int], scope_key: str = "") -> dict[int, str]:
        """The digest state ("pending" | "ready" | "failed") for this scope of each of these cases that has one."""
