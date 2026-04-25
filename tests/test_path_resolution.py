import tempfile
import yaml
from pathlib import Path


def test_relative_path_consistency(project_env, run_puppy):
    """Relative paths in any YAML are resolved relative to the containing file's directory."""
    site_config_dir = project_env['project'] / 'modrinth'
    site_config_dir.mkdir()
    (site_config_dir / 'my_icon.png').write_text('fake_image_data')
    (site_config_dir / 'puppy.yaml').write_text(yaml.dump({'icon': 'my_icon.png'}))

    run_puppy('push', '-n', '-s', 'modrinth')

    temp_icon = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'icon.png'
    assert temp_icon.exists()
