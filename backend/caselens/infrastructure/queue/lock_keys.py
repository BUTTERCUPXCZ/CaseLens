"""Names and time limits of the "only one at a time" locks (see `JobLockRepository`)."""

# A client polling GET /cases?gr_no=...&year=... asks again every few seconds. One fetch job per
# (number, year) is enough; the lock expires so a failed fetch can be tried again later.
FETCH_LOCK_SECONDS = 5 * 60

# Reading ~500 monthly lists at one per second takes about 9 minutes; the lock outlives a build
# but expires, so a crashed worker cannot block new builds forever.
CATALOG_BUILD_KEY = "caselens:build-catalog"
CATALOG_BUILD_LOCK_SECONDS = 60 * 60

# The newest lists change a few times a month. Re-reading them more than once a day would be
# wasted requests to a free library, so the refresh lock lasts a day.
CATALOG_REFRESH_KEY = "caselens:refresh-catalog"
CATALOG_REFRESH_LOCK_SECONDS = 24 * 60 * 60

# The same digest work asked for twice must not pay for the AI twice.
DIGEST_LOCK_SECONDS = 10 * 60


def fetch_case_key(gr_no: str, year: int | None) -> str:
    return f"caselens:fetch-case:{gr_no}:{year}"


def build_digest_key(digest_id: int, keys: list[str] | None) -> str:
    return f"caselens:build-digest:{digest_id}:{','.join(sorted(keys)) if keys else 'all'}"
