import yaml

from puppy.core import Project
from puppy.puller import _harvest_yaml, _merge_results


def _project(tmp_path):
    return Project(tmp_path, override_name='Test', override_handle='test')


def _write_yaml(tmp_path, data: dict):
    (tmp_path / 'puppy.yaml').write_text(yaml.dump(data))


# ── _merge_results ────────────────────────────────────────────────────────────

def test_merge_results_combines_site_keys():
    results = [
        {'config': {'name': 'My Pack'}, 'modrinth': {'id': 'abc', 'license': 'MIT'}},
        {'config': {'summary': 'Cool'}, 'curseforge': {'id': 99, 'license': 'MIT License'}},
    ]
    merged = _merge_results(results)
    assert merged['modrinth'] == {'id': 'abc', 'license': 'MIT'}
    assert merged['curseforge'] == {'id': 99, 'license': 'MIT License'}
    assert merged['config']['name'] == 'My Pack'
    assert merged['config']['summary'] == 'Cool'


def test_merge_results_config_last_wins_for_scalars():
    results = [
        {'config': {'name': 'Old Name'}},
        {'config': {'name': 'New Name'}},
    ]
    merged = _merge_results(results)
    assert merged['config']['name'] == 'New Name'


def test_merge_results_config_skips_empty_values():
    results = [
        {'config': {'name': 'My Pack'}},
        {'config': {'name': None}},
    ]
    merged = _merge_results(results)
    assert merged['config']['name'] == 'My Pack'


def test_merge_results_empty_list():
    assert _merge_results([]) == {}


# ── license promotion ─────────────────────────────────────────────────────────

def test_harvest_yaml_promotes_license_when_all_sites_agree(tmp_path):
    _write_yaml(tmp_path, {'name': 'T', 'modrinth': {'id': 'abc'}, 'curseforge': {'id': 99}})
    result_data = {
        'config': {'name': 'T'},
        'modrinth': {'id': 'abc', 'slug': 'test', 'license': 'MIT'},
        'curseforge': {'id': 99, 'slug': 'test', 'license': 'MIT License'},
    }
    _harvest_yaml(_project(tmp_path), result_data, tmp_path, None, False)
    config = yaml.safe_load((tmp_path / 'puppy.yaml').read_text())
    assert config['license'] == 'MIT'


def test_harvest_yaml_keeps_license_site_specific_when_sites_disagree(tmp_path):
    _write_yaml(tmp_path, {'name': 'T', 'modrinth': {'id': 'abc'}, 'curseforge': {'id': 99}})
    result_data = {
        'config': {'name': 'T'},
        'modrinth': {'id': 'abc', 'slug': 'test', 'license': 'MIT'},
        'curseforge': {'id': 99, 'slug': 'test', 'license': 'Apache License version 2.0'},
    }
    _harvest_yaml(_project(tmp_path), result_data, tmp_path, None, False)
    config = yaml.safe_load((tmp_path / 'puppy.yaml').read_text())
    assert 'license' not in config or config.get('license') is None


def test_harvest_yaml_promotes_license_from_single_site(tmp_path):
    _write_yaml(tmp_path, {'name': 'T', 'curseforge': {'id': 99}})
    result_data = {
        'config': {'name': 'T'},
        'curseforge': {'id': 99, 'slug': 'test', 'license': 'MIT License'},
    }
    _harvest_yaml(_project(tmp_path), result_data, tmp_path, 'curseforge', False)
    config = yaml.safe_load((tmp_path / 'puppy.yaml').read_text())
    assert config['license'] == 'MIT'


def test_harvest_yaml_skips_ambiguous_cf_license(tmp_path):
    _write_yaml(tmp_path, {'name': 'T', 'curseforge': {'id': 99}})
    result_data = {
        'config': {'name': 'T'},
        'curseforge': {'id': 99, 'slug': 'test', 'license': 'Creative Commons 4.0'},
    }
    _harvest_yaml(_project(tmp_path), result_data, tmp_path, 'curseforge', False)
    config = yaml.safe_load((tmp_path / 'puppy.yaml').read_text())
    assert config.get('license') is None


def test_harvest_yaml_writes_images_yaml_on_first_pull_even_without_images_flag(tmp_path):
    _write_yaml(tmp_path, {'name': 'T', 'modrinth': {'id': 'abc'}})
    result_data = {
        'config': {'name': 'T', 'images': [{'file': 'overview', 'description': 'Plains biome'}]},
        'modrinth': {'id': 'abc', 'slug': 'test'},
    }
    _harvest_yaml(_project(tmp_path), result_data, tmp_path, None, images=False)
    images_yaml = tmp_path / 'images' / 'images.yaml'
    assert images_yaml.exists()
    entries = yaml.safe_load(images_yaml.read_text())
    assert entries[0]['description'] == 'Plains biome'


def test_harvest_yaml_does_not_overwrite_images_yaml_when_not_requested(tmp_path):
    _write_yaml(tmp_path, {'name': 'T', 'modrinth': {'id': 'abc'}})
    (tmp_path / 'images').mkdir()
    existing = tmp_path / 'images' / 'images.yaml'
    existing.write_text('- file: old\n  description: keep me\n')
    result_data = {
        'config': {'name': 'T', 'images': [{'file': 'new', 'description': 'replaced'}]},
        'modrinth': {'id': 'abc', 'slug': 'test'},
    }
    _harvest_yaml(_project(tmp_path), result_data, tmp_path, None, images=False)
    entries = yaml.safe_load(existing.read_text())
    assert entries[0]['file'] == 'old'


def test_harvest_yaml_skips_licenseref_from_mr(tmp_path):
    _write_yaml(tmp_path, {'name': 'T', 'modrinth': {'id': 'abc'}})
    result_data = {
        'config': {'name': 'T'},
        'modrinth': {'id': 'abc', 'slug': 'test', 'license': 'LicenseRef-All-Rights-Reserved'},
    }
    _harvest_yaml(_project(tmp_path), result_data, tmp_path, 'modrinth', False)
    config = yaml.safe_load((tmp_path / 'puppy.yaml').read_text())
    assert config.get('license') is None
