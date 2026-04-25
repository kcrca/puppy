import json
import pytest
import puppy.__main__
import yaml
from pathlib import Path


@pytest.fixture
def project_env(tmp_path, monkeypatch):
    """Creates the 'Global > Home > Project' structure from the spec."""
    root = tmp_path / 'neon'
    home = root / 'puppy'
    project = home / 'NeonGlow'
    source = project / 'puppy'

    for d in [home, project, source]:
        d.mkdir(parents=True)

    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'auth.yaml').write_text(
        yaml.dump(
            {
                'modrinth': 'token123',
                'curseforge': {'token': 'cf456'},
            }
        )
    )

    monkeypatch.chdir(project)

    return {'root': root, 'home': home, 'project': project, 'source': source}


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
def run_puppy(monkeypatch):
    """Invokes the CLI directly via the entry point."""

    def _run(*args):
        monkeypatch.setattr('sys.argv', ['puppy'] + list(args))
        try:
            return puppy.__main__.main()
        except SystemExit as e:
            return e.code

    return _run
