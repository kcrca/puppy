import time
import urllib.error
import urllib.request
from typing import Any

# Transient HTTP statuses worth retrying (rate-limit / temporary unavailability).
RETRY_CODES = (429, 503)
MAX_ATTEMPTS = 4


def urlopen_retrying(req: urllib.request.Request, *, timeout: int,
                     retry_codes: tuple = RETRY_CODES, max_attempts: int = MAX_ATTEMPTS) -> Any:
    """urlopen with exponential backoff on transient HTTP statuses.

    Returns the response body bytes. On a retryable status, waits (honoring a
    ``Retry-After`` header when present) and retries; once attempts are exhausted
    the HTTPError propagates so the caller can wrap it (SiteError/AuthExpiredError).
    """
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in retry_codes and attempt < max_attempts - 1:
                retry_after = e.headers.get('Retry-After') if e.headers else None
                try:
                    delay = float(retry_after)
                except (TypeError, ValueError):
                    delay = 2 ** attempt
                time.sleep(delay)
                continue
            raise
