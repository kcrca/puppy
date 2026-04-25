import tempfile
import yaml
from pathlib import Path


def test_sibling_project_url_injection(project_env, run_puppy):
    """Verify that sibling projects are scanned and their URLs injected into Jinja."""
    emerald_root = project_env['home'] / 'Emerald'
    emerald_root.mkdir(parents=True)
    (emerald_root / 'puppy.yaml').write_text(
        yaml.dump({'pack': 'emerald', 'modrinth': {'slug': 'emerald-pack', 'type': 'resourcepack'}})
    )

    (project_env['home'] / 'puppy.yaml').write_text(
        yaml.dump({'projects': ['NeonGlow', 'Emerald']})
    )

    (project_env['project'] / 'description.md').write_text(
        'Check out {{ projects.emerald.modrinth.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'https://modrinth.com/resourcepack/emerald-pack' in debug_file.read_text()
