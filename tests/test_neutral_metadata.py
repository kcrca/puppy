import tempfile
import yaml
from pathlib import Path

from puppy.config import _apply_neutral_metadata


def test_resolution_cf_main_category():
    config = _apply_neutral_metadata({'resolution': 16})
    assert config['curseforge']['mainCategory'] == '16x'


def test_resolution_modrinth_tags_tier_group():
    config = _apply_neutral_metadata({'resolution': 16})
    tags = config['modrinth']['tags']
    assert tags['16x'] is True
    assert tags['8x-'] is False
    assert tags['32x'] is False
    assert tags['512x+'] is False


def test_resolution_pmc_field_and_tags():
    config = _apply_neutral_metadata({'resolution': 16})
    pmc = config['planetminecraft']
    assert pmc['resolution'] == 16
    assert '16x' in pmc['tags']
    assert '16x16' in pmc['tags']


def test_resolution_32x_pmc_tags():
    config = _apply_neutral_metadata({'resolution': 32})
    pmc = config['planetminecraft']
    assert '32x' in pmc['tags']
    assert '32x32' in pmc['tags']
    assert '16x' not in pmc['tags']


def test_per_site_override_wins_over_neutral():
    config = _apply_neutral_metadata(
        {
            'resolution': 16,
            'modrinth': {'tags': {'16x': False}},
        }
    )
    assert config['modrinth']['tags']['16x'] is False
    assert config['curseforge']['mainCategory'] == '16x'


def test_explicit_extra_resolution_tag_preserved():
    config = _apply_neutral_metadata(
        {
            'resolution': 16,
            'modrinth': {'tags': {'8x-': True}},
        }
    )
    assert config['modrinth']['tags']['8x-'] is True
    assert config['modrinth']['tags']['16x'] is True


def test_explicit_cf_main_category_preserved():
    config = _apply_neutral_metadata(
        {
            'resolution': 16,
            'curseforge': {'mainCategory': '32x'},
        }
    )
    assert config['curseforge']['mainCategory'] == '32x'


def test_explicit_pmc_resolution_tag_preserved():
    config = _apply_neutral_metadata(
        {
            'resolution': 16,
            'planetminecraft': {'tags': ['custom-tag']},
        }
    )
    pmc_tags = config['planetminecraft']['tags']
    assert 'custom-tag' in pmc_tags
    assert '16x' in pmc_tags
    assert '16x16' in pmc_tags


def test_progress_pmc():
    config = _apply_neutral_metadata({'progress': 75})
    assert config['planetminecraft']['progress'] == 75


def test_license_cf_and_modrinth():
    config = _apply_neutral_metadata({'license': 'CC-BY-4.0'})
    assert config['curseforge']['license'] == 'CC-BY 4.0'
    assert config['modrinth']['license'] == 'CC-BY-4.0'


def test_license_no_hyphen_unchanged():
    config = _apply_neutral_metadata({'license': 'MIT'})
    assert config['curseforge']['license'] == 'MIT'
    assert config['modrinth']['license'] == 'MIT'


def test_license_per_site_override():
    config = _apply_neutral_metadata(
        {
            'license': 'CC-BY-4.0',
            'curseforge': {'license': 'All Rights Reserved'},
        }
    )
    assert config['curseforge']['license'] == 'All Rights Reserved'
    assert config['modrinth']['license'] == 'CC-BY-4.0'


def test_resolution_expands_to_all_sites(project_env, run_puppy):
    (project_env['source'] / 'puppy.yaml').write_text(yaml.dump({'resolution': 16}))
    run_puppy('push', '-n')

    index = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'index.html'
    ).read_text()
    assert '16x' in index
    assert '16' in index


def test_progress_appears_in_pmc(project_env, run_puppy):
    (project_env['source'] / 'puppy.yaml').write_text(yaml.dump({'progress': 75}))
    run_puppy('push', '-n')

    index = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'index.html'
    ).read_text()
    assert '75%' in index


def test_license_appears_on_cf_and_modrinth(project_env, run_puppy):
    (project_env['source'] / 'puppy.yaml').write_text(yaml.dump({'license': 'MIT'}))
    run_puppy('push', '-n')

    index = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'index.html'
    ).read_text()
    assert 'MIT' in index
