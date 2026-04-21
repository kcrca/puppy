import json
from pathlib import Path

import pytest

from puppy.runner import _patch_settings


@pytest.fixture
def worker_settings(tmp_path):
    worker_dir = tmp_path / 'PackUploader'
    worker_dir.mkdir()
    settings = worker_dir / 'settings.json'
    settings.write_text(
        json.dumps(
            {
                'ewan': True,
                'modrinth': {
                    'discord': 'https://discord.gg/someone',
                    'donation': {'kofi': 'https://ko-fi.com/someone', 'paypal': None},
                },
                'curseforge': {
                    'socials': {'discord': 'https://discord.gg/someone'},
                    'donation': {'type': 'kofi', 'value': 'someone'},
                },
                'planetminecraft': {
                    'website': {
                        'link': 'https://someone.com/',
                        'title': "Someone's site",
                    }
                },
                'templateDefaults': {'discord': 'https://discord.gg/someone'},
            }
        )
    )
    yield settings, worker_dir


def test_worker_flag_cleared(worker_settings):
    settings, worker_dir = worker_settings
    _patch_settings(worker_dir, {})
    data = json.loads(settings.read_text())
    assert data['ewan'] is False


def test_personal_data_cleared(worker_settings):
    settings, worker_dir = worker_settings
    _patch_settings(worker_dir, {})
    data = json.loads(settings.read_text())
    assert data['modrinth']['discord'] is None
    assert data['modrinth']['donation']['kofi'] is None
    assert data['curseforge']['donation']['value'] is None
    assert data['curseforge']['socials']['discord'] is None
    assert data['planetminecraft']['website']['link'] is None
    assert data['templateDefaults'] == {}


def test_config_values_applied(worker_settings):
    settings, worker_dir = worker_settings
    config = {
        'modrinth': {
            'discord': 'https://discord.gg/myserver',
            'donation': {'kofi': 'https://ko-fi.com/me'},
        },
        'curseforge': {'socials': {'discord': 'https://discord.gg/myserver'}},
        'planetminecraft': {
            'website': {'link': 'https://mysite.com', 'title': 'My Site'}
        },
    }
    _patch_settings(worker_dir, config)
    data = json.loads(settings.read_text())
    assert data['modrinth']['discord'] == 'https://discord.gg/myserver'
    assert data['modrinth']['donation']['kofi'] == 'https://ko-fi.com/me'
    assert data['curseforge']['socials']['discord'] == 'https://discord.gg/myserver'
    assert data['planetminecraft']['website']['link'] == 'https://mysite.com'
