import tempfile
import yaml
from pathlib import Path


def test_sibling_links(project_env, run_puppy):
    other = project_env['home'] / 'Other'
    other.mkdir(parents=True)
    (other / 'puppy.yaml').write_text(
        yaml.dump({'pack': 'other', 'modrinth': {'slug': 'other-slug'}})
    )

    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow', 'Other']}))
    (project_env['project'] / 'description.md').write_text(
        'Link: {{ projects.other.modrinth.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'https://modrinth.com/mod/other-slug' in debug_file.read_text()
