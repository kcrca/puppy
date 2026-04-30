import pytest
import yaml
from pathlib import Path

from puppy.checks import check_auth


@pytest.fixture
def auth_home(tmp_path):
    home = tmp_path / 'puppy'
    home.mkdir()
    (home / '.gitignore').write_text('auth.yaml\n')
    return home


def _write_auth(home, data):
    (home / 'auth.yaml').write_text(yaml.dump(data))


def test_valid_auth_passes(auth_home):
    _write_auth(auth_home, {
        'curseforge': {'token': 'abc', 'cookie': 'CobaltSession=xyz'},
        'modrinth': 'token123',
        'planetminecraft': 'pmc_autologin=xyz',
    })
    check_auth(auth_home)


def test_curseforge_missing_cookie(auth_home):
    _write_auth(auth_home, {
        'curseforge': {'token': 'abc'},
        'modrinth': 'token123',
        'planetminecraft': 'pmc_autologin=xyz',
    })
    with pytest.raises(SystemExit, match='cookie'):
        check_auth(auth_home)


def test_curseforge_missing_token(auth_home):
    _write_auth(auth_home, {
        'curseforge': {'cookie': 'CobaltSession=xyz'},
        'modrinth': 'token123',
        'planetminecraft': 'pmc_autologin=xyz',
    })
    with pytest.raises(SystemExit, match='token'):
        check_auth(auth_home)


def test_curseforge_missing_both_keys(auth_home):
    _write_auth(auth_home, {
        'curseforge': {},
        'modrinth': 'token123',
        'planetminecraft': 'pmc_autologin=xyz',
    })
    with pytest.raises(SystemExit, match='curseforge'):
        check_auth(auth_home)
