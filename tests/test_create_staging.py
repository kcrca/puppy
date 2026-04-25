import json
import subprocess
import zipfile
import pytest
import yaml
from PIL import Image

_PACK = 'neonglow'


@pytest.fixture(autouse=True)
def _no_preflight(monkeypatch):
    monkeypatch.setattr('puppy.runner.check_preflight', lambda: None)
    monkeypatch.setattr('puppy.runner._worker_prep', lambda *a, **k: None)


@pytest.fixture
def create_env(project_env, worker_env, monkeypatch):
    source = project_env['source']
    (source / 'puppy.yaml').write_text(
        yaml.dump(
            {
                'name': 'NeonGlow',
                'pack': _PACK,
                'summary': 'A test pack',
                'curseforge': {'id': 111, 'slug': _PACK},
                'modrinth': {'id': 'abc123', 'slug': _PACK},
                'planetminecraft': {'id': 999, 'slug': _PACK},
            }
        )
    )
    Image.new('RGB', (64, 64), color='blue').save(source / 'icon.png')
    with zipfile.ZipFile(source / f'{_PACK}.zip', 'w') as z:
        z.writestr('pack.mcmeta', '{}')

    monkeypatch.setattr(
        'puppy.worker.subprocess.run',
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0),
    )
    return {**project_env, 'worker': worker_env}


def test_create_json_fields(create_env, run_puppy):
    run_puppy('create', '--yes', '--worker', str(create_env['worker']))
    data = json.loads(
        (create_env['worker'] / 'data' / 'create' / 'create.json').read_text()
    )
    assert data['id'] == _PACK
    assert data['name'] == 'NeonGlow'
    assert data['summary'] == 'A test pack'


def test_create_icon_and_zip_staged(create_env, run_puppy):
    run_puppy('create', '--yes', '--worker', str(create_env['worker']))
    assert (create_env['worker'] / 'data' / 'create' / 'pack.png').exists()
    assert (create_env['worker'] / 'data' / 'create' / 'pack.zip').exists()


def test_create_project_json_staged(create_env, run_puppy):
    run_puppy('create', '--yes', '--worker', str(create_env['worker']))
    pj = json.loads(
        (create_env['worker'] / 'projects' / _PACK / 'project.json').read_text()
    )
    assert pj['curseforge']['id'] == 111
    assert pj['modrinth']['id'] == 'abc123'
    assert pj['planetminecraft']['id'] == 999


def test_create_site_filter_nulls_others(create_env, run_puppy):
    run_puppy('create', '--yes', '--site', 'modrinth', '--worker', str(create_env['worker']))
    pj = json.loads(
        (create_env['worker'] / 'projects' / _PACK / 'project.json').read_text()
    )
    assert pj['modrinth']['id'] == 'abc123'
    assert pj['curseforge']['id'] is None
    assert pj['planetminecraft']['id'] is None


def test_create_webp_icon_converted(create_env, run_puppy):
    source = create_env['source']
    Image.new('RGB', (64, 64), color='red').save(source / 'icon.webp')
    config = yaml.safe_load((source / 'puppy.yaml').read_text())
    config['icon'] = 'icon.webp'
    (source / 'puppy.yaml').write_text(yaml.dump(config))

    run_puppy('create', '--yes', '--worker', str(create_env['worker']))
    staged = create_env['worker'] / 'data' / 'create' / 'pack.png'
    assert staged.exists()
    with Image.open(staged) as img:
        assert img.format == 'PNG'


def test_create_calls_worker(create_env, run_puppy, monkeypatch):
    calls = []

    def tracking_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr('puppy.worker.subprocess.run', tracking_run)
    run_puppy('create', '--yes', '--worker', str(create_env['worker']))
    assert any('create.js' in str(c) for c in calls)
