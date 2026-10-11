"""The line printed in a Word file under a decision or digest, naming the library its text came from (as each one asks)."""
from caselens.infrastructure.config import get_settings
from caselens.infrastructure.elibrary.url_scheme import ElibraryUrlScheme

_LAWPHIL = "Lawphil (Arellano Law Foundation), https://lawphil.net"
_ELIBRARY = "the Supreme Court E-Library, https://elibrary.judiciary.gov.ph"


def _from_elibrary(source_url: str | None) -> bool:
    return bool(source_url) and ElibraryUrlScheme(get_settings().elibrary_base_url).is_official_case_url(source_url)


def court_text_notice(source_urls: list[str | None]) -> str:
    """Under the Court's own text (the full-case file). Several cases may come from both libraries."""
    elibrary = [_from_elibrary(url) for url in source_urls]
    if all(elibrary):
        return (
            f"Court text from {_ELIBRARY}. Informational only, not legal advice; the official printed copy of the decision prevails: "
            "confirm with the Supreme Court."
        )
    if any(elibrary):
        return (
            f"Court text from {_LAWPHIL}, and from {_ELIBRARY}. Informational only, not legal advice; neither gives a warranty of "
            "accuracy or completeness: confirm with the Supreme Court."
        )
    return (
        f"Court text from {_LAWPHIL}. Informational only, not legal advice; "
        "Lawphil gives no warranty of accuracy or completeness: confirm with the Supreme Court."
    )


def digest_notice(source_url: str | None) -> str:
    library = _ELIBRARY if _from_elibrary(source_url) else _LAWPHIL
    return (
        f"Written from the Court's decision on {library}. Every sentence is tied to the "
        "decision's paragraphs, but it is a draft: check it against the Court's text. Informational only, not legal advice."
    )
