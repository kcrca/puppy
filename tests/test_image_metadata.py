import tempfile
import yaml
from pathlib import Path

from puppy.config import ConfigSynthesizer


def test_images_yaml_values_are_jinja_expanded(project_env):
    """images.yaml string values are expanded via config strings, not pre-rendered as a template."""
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'pack': 'neonglow'}))
    img_dir = project_env['project'] / 'images'
    img_dir.mkdir()
    (img_dir / 'images.yaml').write_text(
        yaml.dump({'images': [{'file': '{{pack}}_screenshot'}]})
    )

    cfg = ConfigSynthesizer(project_env['home'], project_env['project']).get_running_config()
    assert cfg['images'][0]['file'] == 'neonglow_screenshot'


def test_image_metadata_discovery(project_env, run_puppy):
    """Test that puppy/images/images.yaml is correctly identified."""
    img_dir = project_env['project'] / 'images'
    img_dir.mkdir()
    (img_dir / 'images.yaml').write_text(yaml.dump({'images': [{'file': 'screenshot1.png'}]}))
    (img_dir / 'screenshot1.png').write_text('data')

    run_puppy('push', '-n')

    staged_img = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'images' / 'screenshot1.png'
    )
    assert staged_img.exists()
