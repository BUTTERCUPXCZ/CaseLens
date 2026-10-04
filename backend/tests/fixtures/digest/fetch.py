"""Downloads the sample decisions listed in MANIFEST.txt (one per year, picked at random from the catalog)
into this folder, politely (1 request per second), keeping the raw page bytes. Run once:

    python tests/fixtures/digest/fetch.py
"""
from pathlib import Path

from caselens.infrastructure.config import get_settings
from caselens.infrastructure.lawphil.http_client import ThrottledPageClient

here = Path(__file__).resolve().parent
client = ThrottledPageClient.from_settings(get_settings())
for line in (here / "MANIFEST.txt").read_text().splitlines():
    year, url = line.split()
    target = here / url.rsplit("/", 1)[1]
    if target.exists():
        continue
    html = client.get_text(url)
    if html is None:
        print("MISSING", url)
        continue
    # Saved the way Lawphil serves it (windows-1252, the page declares it), so it decodes like production.
    target.write_bytes(html.encode("cp1252", errors="xmlcharrefreplace"))
    print("saved", target.name, len(html))
