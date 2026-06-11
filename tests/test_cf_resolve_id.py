import json
import urllib.error
import pytest
from unittest.mock import MagicMock, patch

from puppy.sites import CURSEFORGE
from puppy.sites.curseforge import _cf_extract_id_from_page, _CF_DASH


_AUTH = {'curseforge': {'token': 'test-token', 'cookie': 'CobaltSession=x'}}
_AUTH_NO_COOKIE = {'curseforge': {'token': 'test-token'}}
_DASH_HIT = [{'id': 67890, 'slug': 'restworld'}]
_DASH_HIT_PAGINATED = {'data': [{'id': 67890, 'slug': 'restworld'}]}
_DASH_MISS = []


def _make_page_response(html: str):
    resp = MagicMock()
    resp.read.return_value = html.encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ── _cf_extract_id_from_page unit tests ───────────────────────────────────────

def test_extract_id_from_project_id_key():
    assert _cf_extract_id_from_page('"projectId":67890') == 67890


def test_extract_id_from_mod_id_key():
    assert _cf_extract_id_from_page('"modId":12345') == 12345


def test_extract_id_from_next_data():
    html = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({
        'props': {'pageProps': {'project': {'id': 67890, 'slug': 'restworld'}}}
    }) + '</script>'
    assert _cf_extract_id_from_page(html) == 67890


def test_extract_id_from_next_data_mod_key():
    html = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({
        'props': {'pageProps': {'mod': {'id': 99999}}}
    }) + '</script>'
    assert _cf_extract_id_from_page(html) == 99999


def test_extract_id_returns_none_when_not_found():
    assert _cf_extract_id_from_page('<html>nothing here</html>') is None


# ── resolve_id integration ────────────────────────────────────────────────────

def test_resolve_id_skipped_when_id_already_set():
    config = {'curseforge': {'id': 12345, 'slug': 'restworld'}}
    result = CURSEFORGE.resolve_id(config, _AUTH, verbosity=0)
    assert result is config


def test_resolve_id_skipped_when_no_slug():
    config = {'curseforge': {'id': None}}
    result = CURSEFORGE.resolve_id(config, _AUTH, verbosity=0)
    assert result is config


def test_resolve_id_fetches_from_dash_api():
    with patch('puppy.sites.curseforge._cf_get', return_value=_DASH_HIT):
        config = {'type': 'pack', 'curseforge': {'id': None, 'slug': 'restworld'}}
        result = CURSEFORGE.resolve_id(config, _AUTH, verbosity=0)
    assert result['curseforge']['id'] == 67890
    assert result['curseforge']['slug'] == 'restworld'


def test_resolve_id_handles_paginated_response():
    with patch('puppy.sites.curseforge._cf_get', return_value=_DASH_HIT_PAGINATED):
        config = {'type': 'pack', 'curseforge': {'id': None, 'slug': 'restworld'}}
        result = CURSEFORGE.resolve_id(config, _AUTH, verbosity=0)
    assert result['curseforge']['id'] == 67890


def test_resolve_id_preserves_other_fields():
    with patch('puppy.sites.curseforge._cf_get', return_value=_DASH_HIT):
        config = {'type': 'pack', 'curseforge': {'id': None, 'slug': 'restworld', 'category': 17}}
        result = CURSEFORGE.resolve_id(config, _AUTH, verbosity=0)
    assert result['curseforge']['category'] == 17


def test_resolve_id_falls_back_to_page_when_dash_api_misses():
    page = '"projectId":67890'
    with patch('puppy.sites.curseforge._cf_get', return_value=_DASH_MISS):
        with patch('urllib.request.urlopen', return_value=_make_page_response(page)):
            config = {'type': 'pack', 'curseforge': {'id': None, 'slug': 'restworld'}}
            result = CURSEFORGE.resolve_id(config, _AUTH, verbosity=0)
    assert result['curseforge']['id'] == 67890


def test_resolve_id_falls_back_to_page_when_dash_api_raises():
    page = '"projectId":67890'
    with patch('puppy.sites.curseforge._cf_get', side_effect=Exception('oops')):
        with patch('urllib.request.urlopen', return_value=_make_page_response(page)):
            config = {'type': 'pack', 'curseforge': {'id': None, 'slug': 'restworld'}}
            result = CURSEFORGE.resolve_id(config, _AUTH, verbosity=0)
    assert result['curseforge']['id'] == 67890


def test_resolve_id_tries_bedrock_segment_for_world():
    page = '"projectId":67890'
    call_urls = []
    def se(req, **kw):
        call_urls.append(req.full_url)
        if '/minecraft/worlds/' in req.full_url:
            raise urllib.error.HTTPError(None, 404, 'Not Found', {}, None)
        return _make_page_response(page)
    with patch('puppy.sites.curseforge._cf_get', return_value=_DASH_MISS):
        with patch('urllib.request.urlopen', side_effect=se):
            config = {'type': 'world', 'curseforge': {'id': None, 'slug': 'restworld'}}
            result = CURSEFORGE.resolve_id(config, _AUTH, verbosity=0)
    assert result['curseforge']['id'] == 67890
    assert any('mc-addons/worlds' in u for u in call_urls)


def test_resolve_id_raises_when_no_cookie():
    with pytest.raises(SystemExit, match='Could not resolve CurseForge ID'):
        CURSEFORGE.resolve_id(
            {'type': 'pack', 'curseforge': {'id': None, 'slug': 'restworld'}},
            _AUTH_NO_COOKIE,
            verbosity=0,
        )


def test_resolve_id_raises_when_no_page_has_id():
    with patch('puppy.sites.curseforge._cf_get', return_value=_DASH_MISS):
        with patch('urllib.request.urlopen', return_value=_make_page_response('<html>no id</html>')):
            with pytest.raises(SystemExit, match='Could not resolve CurseForge ID'):
                CURSEFORGE.resolve_id(
                    {'type': 'pack', 'curseforge': {'id': None, 'slug': 'x'}},
                    _AUTH,
                    verbosity=0,
                )


def test_resolve_id_raises_on_non_404_page_error():
    def se(req, **kw):
        raise urllib.error.HTTPError(None, 500, 'Server Error', {}, None)
    with patch('puppy.sites.curseforge._cf_get', return_value=_DASH_MISS):
        with patch('urllib.request.urlopen', side_effect=se):
            with pytest.raises(SystemExit, match='Could not resolve CurseForge ID'):
                CURSEFORGE.resolve_id(
                    {'type': 'pack', 'curseforge': {'id': None, 'slug': 'x'}},
                    _AUTH,
                    verbosity=0,
                )
