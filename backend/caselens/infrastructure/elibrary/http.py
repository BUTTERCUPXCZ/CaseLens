import httpx

from caselens.infrastructure.config import Settings
from caselens.infrastructure.elibrary.certificates import elibrary_ssl_context
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient


def elibrary_pages(settings: Settings) -> ThrottledPageClient:
    """The same throttled client as Lawphil's (one page a second, retries, charset handling), with the E-Library's TLS trust."""
    client = httpx.Client(
        headers={"User-Agent": settings.lawphil_user_agent},
        timeout=settings.elibrary_timeout_seconds,
        follow_redirects=True,
        verify=elibrary_ssl_context(),
    )
    return ThrottledPageClient(client, settings.elibrary_min_interval_seconds, settings.elibrary_max_retries)
