import yaml
from pathlib import Path


def test_name_to_slug_derivation_and_writeback(project_env, run_puppy):
    """Spec 2: If only 'name' is provided, 'pack' is derived and written back."""
    config_path = project_env['project'] / 'puppy.yaml'
    config_path.write_text(yaml.dump({'name': 'Super Pack!'}))

    run_puppy('push', '-n', '-s', 'modrinth')

    updated_config = yaml.safe_load(config_path.read_text())
    assert updated_config['name'] == 'Super Pack!'
    assert 'pack' in updated_config
    assert updated_config['pack'] == 'superpack'
