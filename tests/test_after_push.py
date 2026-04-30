import yaml
from pathlib import Path

from puppy.runner import _collect_after_push


def test_no_message_returns_empty():
    assert _collect_after_push({}, None) == []


def test_top_level_message():
    assert _collect_after_push({'after_push': 'Fix the URL!'}, None) == ['Fix the URL!']


def test_site_message_active_site():
    config = {'planetminecraft': {'after_push': 'Update download link'}}
    msgs = _collect_after_push(config, 'planetminecraft')
    assert msgs == ['[PlanetMinecraft] Update download link']


def test_site_message_inactive_site():
    config = {'planetminecraft': {'after_push': 'Update download link'}}
    msgs = _collect_after_push(config, 'modrinth')
    assert msgs == []


def test_site_message_all_sites():
    config = {'planetminecraft': {'after_push': 'Update download link'}}
    msgs = _collect_after_push(config, None)
    assert msgs == ['[PlanetMinecraft] Update download link']


def test_top_level_and_site_message():
    config = {
        'after_push': 'General reminder',
        'planetminecraft': {'after_push': 'Fix PMC link'},
    }
    msgs = _collect_after_push(config, 'planetminecraft')
    assert 'General reminder' in msgs
    assert '[PlanetMinecraft] Fix PMC link' in msgs
    assert len(msgs) == 2


def test_runner_prints_after_push(project_env, run_puppy, monkeypatch, capsys):
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({
            'pack': 'neonglow',
            'after_push': 'Remember to fix the URL!',
            'planetminecraft': {'slug': 'neonglow', 'after_push': 'Check PMC link'},
        })
    )
    monkeypatch.setattr('puppy.runner._worker_prep', lambda *a, **k: None)
    monkeypatch.setattr('puppy.runner._dispatch', lambda *a, **k: None)

    run_puppy('push', '-s', 'planetminecraft')

    out = capsys.readouterr().out
    assert 'Remember to fix the URL!' in out
    assert 'Check PMC link' in out
