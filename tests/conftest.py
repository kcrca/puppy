import json
import pytest
import puppy.__main__
import yaml
from PIL import Image


@pytest.fixture(autouse=True)
def _clear_cf_cache():
    import puppy.sites as sites_mod
    sites_mod._cf_game_versions_cache.clear()
    yield
    sites_mod._cf_game_versions_cache.clear()


@pytest.fixture(autouse=True)
def _no_preflight(monkeypatch):
    monkeypatch.setattr('puppy.runner.check_preflight', lambda: None)


@pytest.fixture(autouse=True)
def _no_cf_native(monkeypatch):
    monkeypatch.setattr('puppy.syncer._run_cf_native', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_mr_native(monkeypatch):
    monkeypatch.setattr('puppy.syncer._run_mr_native', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_mr_native_pull(monkeypatch):
    monkeypatch.setattr('puppy.puller._run_mr_native_pull', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_cf_native_pull(monkeypatch):
    monkeypatch.setattr('puppy.puller._run_cf_native_pull', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_mr_native_upload(monkeypatch):
    monkeypatch.setattr('puppy.publisher.MODRINTH.upload_version', lambda *a, **k: None)


@pytest.fixture
def project_env(tmp_path, monkeypatch):
    """Creates the 'Global > Home > Project' structure from the spec."""
    root = tmp_path / 'neon'
    home = root / 'puppy'
    project = home / 'NeonGlow'

    for d in [home, project]:
        d.mkdir(parents=True)

    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow']}))
    (home / 'auth.yaml').write_text(
        yaml.dump(
            {
                'modrinth': {'token': 'token123'},
                'curseforge': {'token': 'cf456', 'cookie': 'CobaltSession=fake'},
            }
        )
    )

    monkeypatch.chdir(project)

    return {'root': root, 'home': home, 'project': project}


@pytest.fixture
def worker_env(tmp_path):
    """Fake PackUploader directory with rich settings.json for hygiene/staging tests."""
    d = tmp_path / 'PackUploader'
    d.mkdir()
    (d / 'settings.json').write_text(
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
    return d


@pytest.fixture
def push_env(project_env, worker_env, monkeypatch):
    """Project with icon + basic slugs, worker silenced, WORKER_DIR pointed at worker_env."""
    source = project_env['project']
    (source / 'puppy.yaml').write_text(
        yaml.dump(
            {
                'name': 'NeonGlow',
                'pack': 'neonglow',
                'curseforge': {'slug': 'neonglow'},
                'modrinth': {'slug': 'neonglow'},
                'planetminecraft': {'slug': 'neonglow'},
            }
        )
    )
    Image.new('RGB', (64, 64), color='blue').save(source / 'icon.png')
    monkeypatch.setattr('puppy.syncer.worker_prep', lambda *a, **k: None)
    monkeypatch.setattr('puppy.syncer._run_worker', lambda *a, **k: None)
    monkeypatch.setattr('puppy.runner.WORKER_DIR', worker_env)
    return {'worker': worker_env, **project_env}


@pytest.fixture
def run_puppy(monkeypatch):
    """Invokes the CLI directly via the entry point."""

    def _run(*args):
        monkeypatch.setattr('sys.argv', ['puppy', '--no-open'] + list(args))
        try:
            return puppy.__main__.main()
        except SystemExit as e:
            return e.code

    return _run
