import pytest
from puppy.renderer import _SiteProxy


@pytest.fixture
def proxy():
    data = {
        'modrinth': {'url': 'https://modrinth.com/mod/mypack', 'type': 'mod'},
        'curseforge': {'url': 'https://curseforge.com/mypack'},
    }
    return data, lambda site: _SiteProxy(data, site)


def test_explicit_site_access(proxy):
    data, make = proxy
    p = make('modrinth')
    assert p.modrinth == data['modrinth']
    assert p.curseforge == data['curseforge']


def test_site_neutral_resolves_to_current_site(proxy):
    _, make = proxy
    assert make('modrinth').url == 'https://modrinth.com/mod/mypack'
    assert make('curseforge').url == 'https://curseforge.com/mypack'


def test_site_neutral_non_url_attr(proxy):
    _, make = proxy
    assert make('modrinth').type == 'mod'
    assert make('curseforge').type == ''  # curseforge has no 'type'


def test_missing_site_returns_empty_string(proxy):
    _, make = proxy
    assert make('planetminecraft').url == ''


def test_unknown_attr_returns_empty_string(proxy):
    _, make = proxy
    assert make('modrinth').nonexistent == ''


def test_item_access_matches_attr_access(proxy):
    _, make = proxy
    p = make('modrinth')
    assert p['url'] == p.url
    assert p['modrinth'] == p.modrinth
