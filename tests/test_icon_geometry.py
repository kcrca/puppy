import yaml
from PIL import Image


def test_non_square_icon_fails(project_env, run_puppy):
    """A non-1:1 aspect ratio must fail."""
    img = Image.new('RGB', (200, 100), color='blue')
    img.save(project_env['source'] / 'rect.jpg', format='JPEG')
    (project_env['source'] / 'puppy.yaml').write_text(yaml.dump({'icon': 'rect.jpg'}))
    assert run_puppy('push', '-n') != 0
