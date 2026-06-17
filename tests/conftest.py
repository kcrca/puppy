import pytest
import puppy.__main__
import yaml
from PIL import Image


@pytest.fixture(autouse=True)
def _no_images(monkeypatch):
    """Stub phase-1 image work (icon, gallery, URL fetch) so push tests stay offline."""
    monkeypatch.setattr('puppy.syncer._push_images', lambda *a, **k: ({}, None))


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
def _no_cf_push(monkeypatch):
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_mr_push(monkeypatch):
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_mr_pull(monkeypatch):
    monkeypatch.setattr('puppy.puller._run_mr_pull', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_cf_pull(monkeypatch):
    monkeypatch.setattr('puppy.puller._run_cf_pull', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_mr_upload(monkeypatch):
    monkeypatch.setattr('puppy.sites.MODRINTH.upload_version', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_cf_upload(monkeypatch):
    monkeypatch.setattr('puppy.sites.CURSEFORGE.upload_file', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_pmc_push(monkeypatch):
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_pmc_pull(monkeypatch):
    monkeypatch.setattr('puppy.puller._run_pmc_pull', lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _no_pmc_upload(monkeypatch):
    monkeypatch.setattr('puppy.sites.PMC.submit_log', lambda *a, **k: None)


@pytest.fixture
def project_env(tmp_path, monkeypatch):
    """Creates the 'Global > Home > Project' structure from the spec."""
    root = tmp_path / 'neon'
    home = root / 'puppy'
    project = home / 'NeonGlow'

    for d in [home, project]:
        d.mkdir(parents=True)

    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow'], 'type': 'pack'}))
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
def push_env(project_env):
    """Project with icon + basic slugs."""
    source = project_env['project']
    (source / 'puppy.yaml').write_text(
        yaml.dump(
            {
                'name': 'NeonGlow',
                'handle': 'neonglow',
                'type': 'pack',
                'curseforge': {'slug': 'neonglow'},
                'modrinth': {'slug': 'neonglow'},
                'planetminecraft': {'slug': 'neonglow'},
            }
        )
    )
    Image.new('RGB', (64, 64), color='blue').save(source / 'icon.png')
    return project_env


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
