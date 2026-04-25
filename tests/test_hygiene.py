import json
import pytest
import yaml


@pytest.fixture(autouse=True)
def _no_worker(monkeypatch):
    monkeypatch.setattr('puppy.runner.check_preflight', lambda: None)
    monkeypatch.setattr('puppy.runner._worker_prep', lambda *a, **k: None)
    monkeypatch.setattr('puppy.runner._dispatch', lambda *a, **k: None)


def test_worker_flag_cleared(project_env, worker_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'name': 'NeonGlow', 'pack': 'neonglow'})
    )
    run_puppy('push', '--worker', str(worker_env))
    data = json.loads((worker_env / 'settings.json').read_text())
    assert data['ewan'] is False


def test_personal_data_cleared(project_env, worker_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'name': 'NeonGlow', 'pack': 'neonglow'})
    )
    run_puppy('push', '--worker', str(worker_env))
    data = json.loads((worker_env / 'settings.json').read_text())
    assert data['modrinth']['discord'] is None
    assert data['modrinth']['donation']['kofi'] is None
    assert data['curseforge']['donation']['value'] is None
    assert data['curseforge']['socials']['discord'] is None
    assert data['planetminecraft']['website']['link'] is None
    assert data['templateDefaults'] == {}


def test_config_values_applied(project_env, worker_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump(
            {
                'name': 'NeonGlow',
                'pack': 'neonglow',
                'modrinth': {
                    'discord': 'https://discord.gg/myserver',
                    'donation': {'kofi': 'https://ko-fi.com/me'},
                },
                'curseforge': {'socials': {'discord': 'https://discord.gg/myserver'}},
                'planetminecraft': {
                    'website': {'link': 'https://mysite.com', 'title': 'My Site'}
                },
            }
        )
    )
    run_puppy('push', '--worker', str(worker_env))
    data = json.loads((worker_env / 'settings.json').read_text())
    assert data['modrinth']['discord'] == 'https://discord.gg/myserver'
    assert data['modrinth']['donation']['kofi'] == 'https://ko-fi.com/me'
    assert data['curseforge']['socials']['discord'] == 'https://discord.gg/myserver'
    assert data['planetminecraft']['website']['link'] == 'https://mysite.com'
