"""The one place that decides which message broker the application talks to."""
import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.stub import StubBroker

from caselens.infrastructure.config import Settings

LAWPHIL_QUEUE = "lawphil"  # reads from Lawphil: one worker thread, so "1 request per second" holds
DIGEST_QUEUE = "digests"  # AI answers: several worker threads, they only wait for Gemini


def build_broker(settings: Settings) -> dramatiq.Broker:
    """RabbitMQ in production. Its default middleware already gives acknowledgement after the job
    finishes (a crashed worker's job is delivered again), retries with backoff, time limits and a
    dead-letter queue (`<queue>.XQ`) for jobs that kept failing."""
    if settings.queue_backend == "stub":
        return StubBroker()
    return RabbitmqBroker(url=settings.rabbitmq_url)
