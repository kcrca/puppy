import tempfile
import yaml
from pathlib import Path


def test_modrinth_url_type_override(project_env, run_puppy):
    """project_type changes the MR URL segment (modpack -> /modpack/)."""
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'project_type': 'modpack', 'modrinth': {'slug': 'my-pack'}})
    )
    (project_env['project'] / 'description.md').write_text(
        'URL: {{ projects.neonglow.modrinth.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'https://modrinth.com/modpack/my-pack' in debug_file.read_text()
