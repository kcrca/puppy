import tempfile
import yaml
from pathlib import Path


def test_internal_project_linking(project_env, run_puppy):
    """Checks that links to sibling projects are resolved using slugs or IDs."""
    other_home = project_env['home'] / 'OtherMod'
    other_home.mkdir(parents=True)
    (other_home / 'puppy.yaml').write_text(
        yaml.dump({'pack': 'other', 'modrinth': {'slug': 'other-slug'}})
    )

    (project_env['home'] / 'puppy.yaml').write_text(
        yaml.dump({'projects': ['NeonGlow', 'OtherMod']})
    )

    (project_env['project'] / 'description.md').write_text(
        'Link: {{ projects.other.modrinth.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'https://modrinth.com/resourcepack/other-slug' in debug_file.read_text()
