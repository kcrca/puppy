import json
import pytest

from puppy.sites import MODRINTH


class _FakeResponse:
    def __init__(self, data: dict):
        self._data = json.dumps(data).encode()

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


@pytest.fixture
def fake_urlopen(monkeypatch):
    responses = {}

    def _urlopen(req):
        slug = req.full_url.rstrip('/').split('/')[-1]
        if slug not in responses:
            raise Exception(f'No fake response for slug {slug!r}')
        return _FakeResponse(responses[slug])

    monkeypatch.setattr('puppy.sites.urllib.request.urlopen', _urlopen)
    return responses


def test_resolve_id_skipped_when_id_present(fake_urlopen):
    config = {'modrinth': {'id': 'existing', 'slug': 'neon'}}
    result = MODRINTH.resolve_id(config, {}, 0)
    assert result is config
    assert not fake_urlopen


def test_resolve_id_skipped_when_no_slug(fake_urlopen):
    config = {'modrinth': {}}
    result = MODRINTH.resolve_id(config, {}, 0)
    assert result is config
    assert not fake_urlopen


def test_resolve_id_fetches_from_api(fake_urlopen):
    fake_urlopen['neon'] = {'id': 'abc123', 'slug': 'neon'}
    config = {'modrinth': {'slug': 'neon'}}
    result = MODRINTH.resolve_id(config, {'modrinth': 'token'}, 0)
    assert result['modrinth']['id'] == 'abc123'
    assert result['modrinth']['slug'] == 'neon'


def test_resolve_id_raises_on_api_error(fake_urlopen):
    config = {'modrinth': {'slug': 'missing'}}
    with pytest.raises(SystemExit, match="Could not resolve Modrinth ID"):
        MODRINTH.resolve_id(config, {}, 0)


def test_resolve_id_preserves_other_config(fake_urlopen):
    fake_urlopen['neon'] = {'id': 'abc123', 'slug': 'neon'}
    config = {'modrinth': {'slug': 'neon', 'discord': 'https://discord.gg/x'}}
    result = MODRINTH.resolve_id(config, {}, 0)
    assert result['modrinth']['discord'] == 'https://discord.gg/x'
