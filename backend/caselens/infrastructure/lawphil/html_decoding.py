"""Turn the bytes of an HTML page into text using the encoding it actually uses.

Lawphil sends `Content-Type: text/html` with no charset and declares
`<meta ... charset=windows-1252>` inside the page. Left to guess, an HTTP library falls back to
UTF-8 and replaces every curly apostrophe, quote and dash (byte 0x92, 0x93, 0x94, 0x96, ...)
with U+FFFD: 81 of them in one real decision. Court text must not be silently damaged.
"""
import re

_HEADER_CHARSET = re.compile(r"charset\s*=\s*[\"']?\s*([A-Za-z0-9_\-:.]+)", re.IGNORECASE)
_META_CHARSET = re.compile(rb"<meta[^>]+charset\s*=\s*[\"']?\s*([A-Za-z0-9_\-:.]+)", re.IGNORECASE)
_META_SNIFF_BYTES = 4096

# Browsers treat these labels as Windows-1252, and pages that say them really are.
_TREATED_AS_CP1252 = {"iso-8859-1", "latin-1", "latin1", "us-ascii", "ascii", "iso8859-1"}


def decode_html(content: bytes, content_type: str | None = None) -> str:
    """Decode with, in order: the HTTP header's charset, the page's <meta> charset, UTF-8,
    and finally Windows-1252 (damaged characters replaced rather than failing)."""
    candidates: list[str] = []
    if content_type and (header := _HEADER_CHARSET.search(content_type)):
        candidates.append(header.group(1))
    if meta := _META_CHARSET.search(content[:_META_SNIFF_BYTES]):
        candidates.append(meta.group(1).decode("ascii", errors="ignore"))
    candidates.append("utf-8")

    for name in candidates:
        if name.lower() in _TREATED_AS_CP1252:
            name = "cp1252"
        try:
            return content.decode(name)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("cp1252", errors="replace")
