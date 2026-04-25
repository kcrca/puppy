import tempfile
import yaml
from pathlib import Path


def test_site_and_project_specific_priority(project_env, run_puppy):
    """Project-site-specific file should be the final winner in the cascade."""
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'status': 'project-general'}))

    ps_dir = project_env['project'] / 'modrinth'
    ps_dir.mkdir()
    (ps_dir / 'puppy.yaml').write_text(yaml.dump({'status': 'project-site-specific'}))

    (project_env['project'] / 'description.md').write_text('{{ status }}')
    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'project-site-specific' in debug_file.read_text()
