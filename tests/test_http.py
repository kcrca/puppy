import io
import urllib.error
import urllib.request

import pytest

from puppy.http import MAX_ATTEMPTS, MAX_DELAY, urlopen_retrying


def _http_error(code: int, body: bytes = b'', hdrs=None):
    return urllib.error.HTTPError('', code, '', hdrs or {}, io.BytesIO(body))


class _Resp:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self) -> bytes:
        return self._body


def test_retries_on_429_then_succeeds(monkeypatch):
    seq = [
        _http_error(429, b'throttled', {'Retry-After': '0'}),
        _http_error(429, b'throttled'),
        _Resp(b'{"ok": true}'),
    ]
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(1)
        r = seq[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr('time.sleep', lambda *a, **k: None)
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    assert urlopen_retrying(urllib.request.Request('https://x'), timeout=30) == b'{"ok": true}'
    assert len(calls) == 3   # two 429s retried, third succeeded


def test_raises_after_max_attempts(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(1)
        raise _http_error(429, b'throttled')

    monkeypatch.setattr('time.sleep', lambda *a, **k: None)
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    with pytest.raises(urllib.error.HTTPError):
        urlopen_retrying(urllib.request.Request('https://x'), timeout=30)
    assert len(calls) == MAX_ATTEMPTS


def test_503_also_retries(monkeypatch):
    seq = [_http_error(503), _Resp(b'ok')]
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(1)
        r = seq[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr('time.sleep', lambda *a, **k: None)
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    assert urlopen_retrying(urllib.request.Request('https://x'), timeout=30) == b'ok'
    assert len(calls) == 2


def test_non_retryable_raises_immediately(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(1)
        raise _http_error(404)

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    with pytest.raises(urllib.error.HTTPError):
        urlopen_retrying(urllib.request.Request('https://x'), timeout=30)
    assert len(calls) == 1   # 404 is not retried


def test_urlerror_retries_then_succeeds(monkeypatch):
    seq = [urllib.error.URLError('connection reset'), _Resp(b'ok')]
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(1)
        r = seq[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr('time.sleep', lambda *a, **k: None)
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    assert urlopen_retrying(urllib.request.Request('https://x'), timeout=30) == b'ok'
    assert len(calls) == 2


def test_urlerror_raises_after_max_attempts(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(1)
        raise urllib.error.URLError('timeout')

    monkeypatch.setattr('time.sleep', lambda *a, **k: None)
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    with pytest.raises(urllib.error.URLError):
        urlopen_retrying(urllib.request.Request('https://x'), timeout=30)
    assert len(calls) == MAX_ATTEMPTS


def test_retry_after_is_capped(monkeypatch):
    sleeps = []
    seq = [_http_error(429, b'', {'Retry-After': '3600'}), _Resp(b'ok')]
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(1)
        r = seq[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr('time.sleep', lambda d: sleeps.append(d))
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    urlopen_retrying(urllib.request.Request('https://x'), timeout=30)
    assert sleeps == [MAX_DELAY]   # 3600 clamped to the cap
