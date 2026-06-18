import time
import urllib.error
import urllib.request
from typing import Any

# Transient HTTP statuses worth retrying (rate-limit / temporary unavailability).
RETRY_CODES = (429, 503)
MAX_ATTEMPTS = 4
MAX_DELAY = 60  # cap any single backoff sleep, in seconds


def _retry_delay(e: urllib.error.HTTPError, attempt: int) -> float:
    """Backoff for a retryable HTTPError: honor Retry-After if present, else
    exponential — capped so a hostile/garbage header can't stall the run."""
    retry_after = e.headers.get('Retry-After') if e.headers else None
    try:
        delay = float(retry_after)
    except (TypeError, ValueError):
        delay = 2 ** attempt
    return min(delay, MAX_DELAY)


def urlopen_retrying(req: urllib.request.Request, *, timeout: int,
                     retry_codes: tuple = RETRY_CODES, max_attempts: int = MAX_ATTEMPTS) -> Any:
    """urlopen with exponential backoff on transient failures.

    Returns the response body bytes. Retries on a retryable HTTP status (honoring a
    ``Retry-After`` header when present) and on network-level errors (connection
    reset, timeout, DNS). Once attempts are exhausted the error propagates so the
    caller can wrap it (SiteError/AuthExpiredError).
    """
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in retry_codes and attempt < max_attempts - 1:
                time.sleep(_retry_delay(e, attempt))
                continue
            raise
        except urllib.error.URLError:
            # network-level transient (reset/timeout/DNS); HTTPError handled above
            if attempt < max_attempts - 1:
                time.sleep(min(2 ** attempt, MAX_DELAY))
                continue
            raise
