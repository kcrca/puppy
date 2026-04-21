from PIL import Image
import tempfile
from pathlib import Path


def test_jpg_to_png_conversion_for_worker(project_env, run_puppy):
    """The worker always expects PNG. Puppy should convert JPG gallery images automatically."""
    img_dir = project_env['source'] / 'images'
    img_dir.mkdir()

    # Create a JPG
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(img_dir / 'screen.jpg')

    # metadata omitting extension
    (img_dir / 'images.yaml').write_text(
        "images:\n  - file: 'screen'\n    name: 'Screenshot'"
    )

    run_puppy('push', '-n')

    # The staged area for the worker MUST have a .png version
    staged_img = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'images' / 'screen.png'
    )
    assert staged_img.exists()
