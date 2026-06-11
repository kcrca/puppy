import pytest
from unittest.mock import MagicMock, patch

from puppy.sites import PMC


_AUTH = {'planetminecraft': {'cookie': 'pmc_autologin=test'}}


def _make_response(body: str, status: int = 200):
    resp = MagicMock()
    resp.read.return_value = body.encode() if isinstance(body, str) else body
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_resolve_id_skipped_when_id_already_set():
    config = {'type': 'pack', 'planetminecraft': {'id': 6911690, 'slug': 'creamy-6911690'}}
    result = PMC.resolve_id(config, _AUTH, verbosity=0)
    assert result is config


def test_resolve_id_skipped_when_no_slug():
    config = {'type': 'pack', 'planetminecraft': {'id': None}}
    result = PMC.resolve_id(config, _AUTH, verbosity=0)
    assert result is config


def test_resolve_id_extracts_id_from_slug():
    config = {'type': 'pack', 'planetminecraft': {'id': None, 'slug': 'creamy-6911690'}}
    result = PMC.resolve_id(config, {}, verbosity=0)
    assert result['planetminecraft']['id'] == 6911690


def test_resolve_id_extracts_id_from_world_slug():
    config = {'type': 'world', 'planetminecraft': {'id': None, 'slug': 'restworld-1234567'}}
    result = PMC.resolve_id(config, {}, verbosity=0)
    assert result['planetminecraft']['id'] == 1234567


def test_resolve_id_preserves_other_fields():
    config = {'type': 'pack', 'planetminecraft': {'id': None, 'slug': 'creamy-6911690', 'resolution': 16}}
    result = PMC.resolve_id(config, {}, verbosity=0)
    assert result['planetminecraft']['resolution'] == 16


def test_resolve_id_fetches_page_when_slug_has_no_id():
    html = '<html><a href="/account/manage/texture-packs/6911690/edit">Edit</a></html>'
    with patch('urllib.request.urlopen', return_value=_make_response(html)):
        config = {'type': 'pack', 'planetminecraft': {'id': None, 'slug': 'creamy'}}
        result = PMC.resolve_id(config, {}, verbosity=0)
    assert result['planetminecraft']['id'] == 6911690


def test_resolve_id_world_fetches_page_with_projects_path():
    html = '<html><a href="/account/manage/projects/1234567/edit">Edit</a></html>'
    with patch('urllib.request.urlopen', return_value=_make_response(html)):
        config = {'type': 'world', 'planetminecraft': {'id': None, 'slug': 'restworld'}}
        result = PMC.resolve_id(config, {}, verbosity=0)
    assert result['planetminecraft']['id'] == 1234567


def test_resolve_id_uses_og_url_fallback():
    html = '<html><meta property="og:url" content="https://www.planetminecraft.com/texture-pack/creamy-6911690/"></html>'
    with patch('urllib.request.urlopen', return_value=_make_response(html)):
        config = {'type': 'pack', 'planetminecraft': {'id': None, 'slug': 'creamy'}}
        result = PMC.resolve_id(config, {}, verbosity=0)
    assert result['planetminecraft']['id'] == 6911690


def test_resolve_id_raises_when_page_has_no_id():
    html = '<html><body>No ID here</body></html>'
    with patch('urllib.request.urlopen', return_value=_make_response(html)):
        with pytest.raises(SystemExit, match='Could not find PlanetMinecraft ID'):
            PMC.resolve_id({'type': 'pack', 'planetminecraft': {'id': None, 'slug': 'unknown'}}, {}, verbosity=0)


def test_resolve_id_raises_on_http_error():
    import urllib.error
    with patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError(None, 404, 'Not Found', {}, None)):
        with pytest.raises(SystemExit, match='Could not resolve PlanetMinecraft ID'):
            PMC.resolve_id({'type': 'pack', 'planetminecraft': {'id': None, 'slug': 'unknown'}}, {}, verbosity=0)
