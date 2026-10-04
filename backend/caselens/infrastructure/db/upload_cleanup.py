import logging
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from caselens.infrastructure.db.orm_models import UploadModel
from caselens.infrastructure.db.session import SessionLocal

logger = logging.getLogger(__name__)

_EVERY_SECONDS = 6 * 3600


def delete_old_uploads(session: Session, keep_days: int) -> int:
    """Delete uploads older than `keep_days` (their citations and digests go with them; saved cases stay)."""
    cutoff = datetime.now(UTC) - timedelta(days=keep_days)
    deleted = session.execute(delete(UploadModel).where(UploadModel.created_at < cutoff)).rowcount
    session.commit()
    if deleted:
        logger.info("deleted %d upload(s) older than %d days", deleted, keep_days)
    return deleted


def keep_uploads_trimmed(keep_days: int) -> None:
    """Runs now and then every 6 hours, on a background thread, until the process stops."""

    def loop() -> None:
        stop = threading.Event()
        while True:
            try:
                with SessionLocal() as session:
                    delete_old_uploads(session, keep_days)
            except Exception:
                logger.exception("upload clean-up failed")
            stop.wait(_EVERY_SECONDS)

    threading.Thread(target=loop, name="upload-cleanup", daemon=True).start()
