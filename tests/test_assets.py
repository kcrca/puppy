import tempfile
import yaml
from pathlib import Path

from PIL import Image


def test_image_conversion_and_validation(project_env, run_puppy):
    img = Image.new('RGB', (100, 100), color='red')
    img.save(project_env['project'] / 'icon.webp')
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'icon': 'icon.webp'}))

    run_puppy('push', '-n')

    staged_icon = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'icon.png'
    assert staged_icon.exists()

    bad_img = Image.new('RGB', (200, 100))
    bad_img.save(project_env['project'] / 'bad.png')
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'icon': 'bad.png'}))
    assert run_puppy('push', '-n') != 0
