from caselens.application.ports.gateways import JobQueue
from caselens.application.ports.repositories import UnitOfWork, UploadRepository
from caselens.domain.errors import CaseNotFoundError
from caselens.domain.value_objects import MatchStatus


class RetryUpload:
    """Check again the citations that failed for a temporary reason (source down, page
    unreadable). Citations that were simply not found are left alone: asking again would
    give the same answer."""

    def __init__(self, uploads: UploadRepository, jobs: JobQueue, uow: UnitOfWork) -> None:
        self._uploads = uploads
        self._jobs = jobs
        self._uow = uow

    def execute(self, upload_id: int) -> None:
        upload = self._uploads.get(upload_id)
        if upload is None:
            raise CaseNotFoundError(f"Upload {upload_id} does not exist.")

        failed = [c for c in upload.citations if c.status is MatchStatus.ERROR]
        if not failed:
            return
        for citation in failed:
            citation.reset_for_retry()
        upload.status = "processing"
        self._uploads.save(upload)
        self._uow.commit()  # commit first so the worker sees the reset
        self._jobs.enqueue_resolve_upload(upload_id)
