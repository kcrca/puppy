import tempfile
import yaml
from pathlib import Path

from PIL import Image


def test_jpg_to_png_conversion_for_worker(project_env, run_puppy):
    """The worker always expects PNG. Puppy should convert JPG gallery images automatically."""
    img_dir = project_env['source'] / 'images'
    img_dir.mkdir()

    img = Image.new('RGB', (100, 100), color='blue')
    img.save(img_dir / 'screen.jpg')

    (img_dir / 'images.yaml').write_text(
        yaml.dump({'images': [{'file': 'screen', 'name': 'Screenshot'}]})
    )

    run_puppy('push', '-n')

    staged_img = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'images' / 'screen.png'
    assert staged_img.exists()
