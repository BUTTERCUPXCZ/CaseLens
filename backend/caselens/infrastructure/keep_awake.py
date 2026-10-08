"""The website on a free host sleeps after some minutes without visitors, and work running inside it (a bulk upload, a digest) stops
with it; on waking it starts again from the top, and that costs AI again. While work is waiting or running, the site calls its own
public address now and then, which counts as a visitor. With nothing left to do it is left to sleep, so free hours are not spent."""
import logging
import threading
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, or_, select

from caselens.infrastructure.db.orm_models import BulkItemModel, CaseDigestV2Model, CaseQuestionModel, UploadModel
from caselens.infrastructure.db.session import SessionLocal

logger = logging.getLogger(__name__)

EVERY_SECONDS = 10 * 60  # Render's free plan sleeps after 15 minutes without a request
_RECENT = timedelta(days=7)  # as the restart recovery: older unfinished work is not picked up again either


def work_is_waiting(session_factory=SessionLocal) -> bool:
    """Anything queued or being written: a case digest, a bulk item, an upload or a question."""
    since = datetime.now(UTC) - _RECENT
    with session_factory() as session:
        return bool(
            session.scalar(
                select(
                    or_(
                        exists().where(CaseDigestV2Model.state == "pending"),
                        exists().where(BulkItemModel.status == "queued"),
                        exists().where(UploadModel.status == "processing", UploadModel.created_at >= since),
                        exists().where(CaseQuestionModel.state == "pending", CaseQuestionModel.created_at >= since),
                    )
                )
            )
        )


def _ping(url: str) -> None:
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 (our own https address, from the host)
        response.read()


def keep_awake_while_busy(
    public_url: str,
    *,
    has_work: Callable[[], bool] = work_is_waiting,
    ping: Callable[[str], None] = _ping,
    every: float = EVERY_SECONDS,
    stop: threading.Event | None = None,
) -> threading.Thread:
    """Every `every` seconds, while there is work, GET `<public_url>/health`. Runs on a background thread until `stop` is set."""
    stop = stop or threading.Event()
    target = public_url.rstrip("/") + "/health"

    def loop() -> None:
        while not stop.wait(every):
            try:
                if has_work():
                    ping(target)
            except Exception:  # a failed ping is tried again next time; it never stops the site
                logger.warning("keep-awake: could not reach %s", target, exc_info=True)

    thread = threading.Thread(target=loop, name="keep-awake", daemon=True)
    thread.start()
    return thread
