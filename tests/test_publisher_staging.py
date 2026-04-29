import json
import subprocess
import zipfile
import pytest
import yaml
from PIL import Image

from puppy.core import Project
from puppy.sites import PMC

_PACK = 'neonglow'
_VERSION = '1.0.0'


@pytest.fixture(autouse=True)
def _no_run_worker(monkeypatch):
    monkeypatch.setattr('puppy.runner._worker_prep', lambda *a, **k: None)
    monkeypatch.setattr('puppy.syncer._run_worker', lambda *a, **k: None)


@pytest.fixture
def push_pack_env(project_env, worker_env, monkeypatch):
    source = project_env['project']
    Image.new('RGB', (64, 64), color='blue').save(source / 'icon.png')
    with zipfile.ZipFile(source / f'{_PACK}-{_VERSION}.zip', 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    (source / 'puppy.yaml').write_text(
        yaml.dump(
            {
                'name': 'NeonGlow',
                'pack': _PACK,
                'minecraft': '1.20',
                'curseforge': {'id': 111, 'slug': _PACK},
                'modrinth': {'id': 'abc123', 'slug': _PACK},
                'planetminecraft': {'id': 999, 'slug': _PACK},
            }
        )
    )
    monkeypatch.setattr(
        'puppy.publisher.subprocess.run',
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0),
    )
    return {**project_env, 'worker': worker_env}


def _run_push_pack(run_puppy, worker, site=None):
    args = ['push', '--pack', '--force', '--version', _VERSION, '--worker', str(worker)]
    if site:
        args += ['--site', site]
    run_puppy(*args)


def test_update_json_staged(push_pack_env, run_puppy):
    _run_push_pack(run_puppy, push_pack_env['worker'])
    data = json.loads(
        (push_pack_env['worker'] / 'data' / 'update' / 'update.json').read_text()
    )
    assert data['id'] == _PACK
    assert data['version'] == _VERSION
    assert (push_pack_env['worker'] / 'data' / 'update' / 'pack.zip').exists()


def test_patch_project_json_nulls_skipped_sites(push_pack_env, run_puppy):
    _run_push_pack(run_puppy, push_pack_env['worker'], site='modrinth')
    pj = json.loads(
        (push_pack_env['worker'] / 'projects' / _PACK / 'project.json').read_text()
    )
    assert pj['modrinth']['id'] == 'abc123'
    assert pj['curseforge']['id'] is None
    assert pj['planetminecraft']['id'] is None


def test_patch_project_json_all_sites(push_pack_env, run_puppy):
    _run_push_pack(run_puppy, push_pack_env['worker'])
    pj = json.loads(
        (push_pack_env['worker'] / 'projects' / _PACK / 'project.json').read_text()
    )
    assert pj['curseforge']['id'] == 111
    assert pj['modrinth']['id'] == 'abc123'
    assert pj['planetminecraft']['id'] == 999


def test_save_and_check_pmc_version(tmp_path):
    puppy_dir = tmp_path
    zip_path = puppy_dir / 'mypack-1.0.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    project = Project(tmp_path, override_name='MyPack', override_pack='mypack')

    assert PMC.needs_upload(999, {}, zip_path, '1.0.0', project) is True
    PMC.post_upload(puppy_dir, '1.0.0')
    assert PMC.needs_upload(999, {}, zip_path, '1.0.0', project) is False
    assert PMC.needs_upload(999, {}, zip_path, '1.0.1', project) is True
