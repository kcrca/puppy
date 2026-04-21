import json
import subprocess
from pathlib import Path

import pytest
import yaml

from puppy.core import Project
from puppy.importer import _stage, _harvest_yaml, run_import


@pytest.fixture
def project_setup(tmp_path):
    project_root = tmp_path / 'MyPack'
    puppy_dir = project_root / 'puppy'
    puppy_dir.mkdir(parents=True)

    config = {
        'name': 'MyPack',
        'pack': 'mypack',
        'curseforge': {'id': 111, 'slug': 'mypack'},
        'modrinth': {'id': 'abc123', 'slug': 'mypack'},
        'planetminecraft': {'id': 999, 'slug': 'mypack'},
    }
    project = Project(project_root, override_name='MyPack', override_pack='mypack')
    return project, config, puppy_dir


@pytest.fixture
def worker_dir(tmp_path):
    d = tmp_path / 'worker'
    d.mkdir()
    return d


def test_import_json_staged(project_setup, worker_dir):
    project, config, puppy_dir = project_setup
    _stage(project, config, worker_dir, site=None)

    data = json.loads((worker_dir / 'data' / 'import.json').read_text())
    assert data['id'] == 'mypack'
    assert data['curseforge']['id'] == 111
    assert data['modrinth']['id'] == 'abc123'
    assert data['planetminecraft']['id'] == 999


def test_import_site_filter_nulls_others(project_setup, worker_dir):
    project, config, puppy_dir = project_setup
    _stage(project, config, worker_dir, site='modrinth')

    data = json.loads((worker_dir / 'data' / 'import.json').read_text())
    assert data['modrinth']['id'] == 'abc123'
    assert data['curseforge']['id'] is None
    assert data['planetminecraft']['id'] is None


def test_harvest_yaml_writes_ids(project_setup):
    project, config, puppy_dir = project_setup
    result_data = {
        'config': {'name': 'MyPack', 'summary': 'A great pack', 'version': '1.2.0'},
        'curseforge': {'id': 111, 'slug': 'mypack'},
        'modrinth': {'id': 'abc123', 'slug': 'mypack'},
        'planetminecraft': {'id': 999, 'slug': 'mypack'},
    }
    _harvest_yaml(project, result_data, puppy_dir, site=None)

    written = yaml.safe_load((puppy_dir / 'puppy.yaml').read_text())
    assert written['curseforge']['id'] == 111
    assert written['modrinth']['id'] == 'abc123'
    assert written['name'] == 'MyPack'
    assert written['version'] == '1.2.0'


def test_harvest_yaml_site_filter(project_setup):
    project, config, puppy_dir = project_setup
    result_data = {
        'config': {'name': 'MyPack'},
        'modrinth': {'id': 'abc123', 'slug': 'mypack'},
    }
    _harvest_yaml(project, result_data, puppy_dir, site='modrinth')

    written = yaml.safe_load((puppy_dir / 'puppy.yaml').read_text())
    assert written['modrinth']['id'] == 'abc123'
    assert 'curseforge' not in written
    assert 'planetminecraft' not in written


def test_run_import_calls_worker(project_setup, worker_dir, monkeypatch):
    project, config, puppy_dir = project_setup
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        project_dir = worker_dir / 'projects' / 'mypack'
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / 'project.json').write_text(
            json.dumps(
                {
                    'config': {'name': 'MyPack'},
                    'curseforge': {'id': 111, 'slug': 'mypack'},
                    'modrinth': {'id': 'abc123', 'slug': 'mypack'},
                    'planetminecraft': {'id': 999, 'slug': 'mypack'},
                }
            )
        )
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, 'run', fake_run)

    run_import(
        project=project,
        config=config,
        auth={},
        worker_dir=worker_dir,
        site=None,
        verbosity=0,
    )
    assert any('import.js' in ' '.join(c) for c in calls)
