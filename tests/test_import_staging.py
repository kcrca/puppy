import json
import subprocess
import pytest
import yaml

_PACK = 'neonglow'
_PROJECT_JSON = {
    'config': {'name': 'NeonGlow', 'summary': 'A pack', 'version': '1.0.0'},
    'curseforge': {'id': 111, 'slug': _PACK},
    'modrinth': {'id': 'abc123', 'slug': _PACK},
    'planetminecraft': {'id': 999, 'slug': _PACK},
}


def _write_project_json(worker_dir, data=None):
    pd = worker_dir / 'projects' / _PACK
    pd.mkdir(parents=True, exist_ok=True)
    (pd / 'project.json').write_text(json.dumps(data or _PROJECT_JSON))


@pytest.fixture(autouse=True)
def _no_preflight(monkeypatch):
    monkeypatch.setattr('puppy.runner.check_preflight', lambda: None)
    monkeypatch.setattr('puppy.runner._worker_prep', lambda *a, **k: None)


@pytest.fixture
def import_env(project_env, worker_env, monkeypatch):
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump(
            {
                'name': 'NeonGlow',
                'pack': _PACK,
                'curseforge': {'id': 111, 'slug': _PACK},
                'modrinth': {'id': 'abc123', 'slug': _PACK},
                'planetminecraft': {'id': 999, 'slug': _PACK},
            }
        )
    )

    def fake_run(cmd, **kwargs):
        _write_project_json(worker_env)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr('puppy.worker.subprocess.run', fake_run)
    return {**project_env, 'worker': worker_env}


def test_import_json_staged(import_env, run_puppy):
    run_puppy('import', '--worker', str(import_env['worker']))
    data = json.loads((import_env['worker'] / 'data' / 'import.json').read_text())
    assert data['id'] == _PACK
    assert data['curseforge']['id'] == 111
    assert data['modrinth']['id'] == 'abc123'
    assert data['planetminecraft']['id'] == 999


def test_import_site_filter_nulls_others(import_env, run_puppy, monkeypatch):
    def fake_run_mr(cmd, **kwargs):
        pd = import_env['worker'] / 'projects' / _PACK
        pd.mkdir(parents=True, exist_ok=True)
        (pd / 'project.json').write_text(
            json.dumps({'config': {'name': 'NeonGlow'}, 'modrinth': {'id': 'abc123', 'slug': _PACK}})
        )
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr('puppy.worker.subprocess.run', fake_run_mr)
    run_puppy('import', '--site', 'modrinth', '--worker', str(import_env['worker']))
    data = json.loads((import_env['worker'] / 'data' / 'import.json').read_text())
    assert data['modrinth']['id'] == 'abc123'
    assert data['curseforge']['id'] is None
    assert data['planetminecraft']['id'] is None


def test_harvest_yaml_writes_ids(import_env, run_puppy):
    run_puppy('import', '--worker', str(import_env['worker']))
    written = yaml.safe_load((import_env['project'] / 'puppy.yaml').read_text())
    assert written['curseforge']['id'] == 111
    assert written['modrinth']['id'] == 'abc123'
    assert written['name'] == 'NeonGlow'
    assert written['version'] == '1.0.0'


def test_harvest_yaml_site_filter(project_env, worker_env, run_puppy, monkeypatch):
    monkeypatch.setattr('puppy.worker.subprocess.run', lambda cmd, **kw: (
        _write_project_json(
            worker_env,
            {'config': {'name': 'NeonGlow'}, 'modrinth': {'id': 'abc123', 'slug': _PACK}},
        ) or subprocess.CompletedProcess(cmd, 0)
    ))
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'name': 'NeonGlow', 'pack': _PACK, 'modrinth': {'id': 'abc123', 'slug': _PACK}})
    )
    run_puppy('import', '--site', 'modrinth', '--worker', str(worker_env))
    written = yaml.safe_load((project_env['project'] / 'puppy.yaml').read_text())
    assert written.get('modrinth', {}).get('id') == 'abc123'
    assert 'curseforge' not in written
    assert 'planetminecraft' not in written


def test_import_calls_worker(import_env, run_puppy, monkeypatch):
    calls = []

    def tracking_run(cmd, **kwargs):
        calls.append(cmd)
        _write_project_json(import_env['worker'])
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr('puppy.worker.subprocess.run', tracking_run)
    run_puppy('import', '--worker', str(import_env['worker']))
    assert any('import.js' in str(c) for c in calls)
