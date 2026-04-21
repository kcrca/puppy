import tempfile
import yaml
from pathlib import Path


def test_relative_path_consistency(project_env, run_puppy):
    """Spec 5.5: Relative paths in any YAML are resolved relative to the project's puppy/ directory."""
    (project_env['source'] / 'my_icon.png').write_text('fake_image_data')

    site_config_dir = project_env['source'] / 'modrinth'
    site_config_dir.mkdir()
    (site_config_dir / 'puppy.yaml').write_text(yaml.dump({'icon': 'my_icon.png'}))

    run_puppy('push', '-n', '-s', 'modrinth')

    temp_icon = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'icon.png'
    assert temp_icon.exists()
