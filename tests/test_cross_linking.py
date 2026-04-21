import tempfile
import yaml
from pathlib import Path


def test_cross_project_url_resolution(project_env, run_puppy):
    """Test {{ projects.[other].url }} resolution."""
    other_proj = project_env['home'] / 'OtherMod'
    other_proj.mkdir()
    (other_proj / 'puppy').mkdir()
    (other_proj / 'puppy' / 'puppy.yaml').write_text(
        yaml.dump({'pack': 'other', 'modrinth': {'id': 'abc'}})
    )

    (project_env['source'] / 'description.md').write_text(
        'Link: {{ projects.other.modrinth.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'https://modrinth.com/mod/abc' in debug_file.read_text()
