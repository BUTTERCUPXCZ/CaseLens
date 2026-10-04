from caselens.application.ports.repositories import UploadRepository
from caselens.domain.entities import UploadSummary


class ListUploads:
    def __init__(self, uploads: UploadRepository) -> None:
        self._uploads = uploads

    def execute(self, limit: int = 20) -> list[UploadSummary]:
        return self._uploads.list_recent(limit)
