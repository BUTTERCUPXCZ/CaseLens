from caselens.application.ports.repositories import UnitOfWork, UploadRepository
from caselens.domain.errors import CaseNotFoundError


class DeleteUpload:
    """The student removes a reviewer they uploaded, with its digest boxes. The cases it cited stay in the case
    library: they are the Court's text, not the student's file."""

    def __init__(self, uploads: UploadRepository, uow: UnitOfWork) -> None:
        self._uploads = uploads
        self._uow = uow

    def execute(self, upload_id: int) -> None:
        if not self._uploads.delete(upload_id):
            raise CaseNotFoundError(f"Upload {upload_id} does not exist.")
        self._uow.commit()
