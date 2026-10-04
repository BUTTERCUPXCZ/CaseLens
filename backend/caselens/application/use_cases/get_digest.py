from caselens.application.ports.digests import DigestRepository
from caselens.domain.case_digest import CaseDigest
from caselens.domain.errors import DigestNotFoundError


class GetDigest:
    def __init__(self, digests: DigestRepository) -> None:
        self._digests = digests

    def by_id(self, digest_id: int) -> CaseDigest:
        digest = self._digests.get(digest_id)
        if digest is None:
            raise DigestNotFoundError(f"Digest {digest_id} does not exist.")
        return digest

    def for_case(self, case_id: int, upload_id: int | None) -> CaseDigest:
        digest = self._digests.find(case_id, upload_id)
        if digest is None:
            raise DigestNotFoundError("This case has no digest yet.")
        return digest

    def for_upload(self, upload_id: int) -> list[CaseDigest]:
        return self._digests.list_for_upload(upload_id)
