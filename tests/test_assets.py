from PIL import Image
import tempfile
from pathlib import Path


def test_image_conversion_and_validation(project_env, run_puppy):
    # Valid WebP -> PNG conversion
    img = Image.new('RGB', (100, 100), color='red')
    img.save(project_env['source'] / 'icon.webp')
    (project_env['source'] / 'puppy.yaml').write_text("icon: 'icon.webp'")

    run_puppy('push', '-n')

    staged_icon = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'icon.png'
    assert staged_icon.exists()

    # Non-square failure
    bad_img = Image.new('RGB', (200, 100))
    bad_img.save(project_env['source'] / 'bad.png')
    (project_env['source'] / 'puppy.yaml').write_text("icon: 'bad.png'")
    assert run_puppy('push', '-n') != 0
