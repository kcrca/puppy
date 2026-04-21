from PIL import Image
import tempfile
from pathlib import Path


def test_transparency_preserved_on_conversion(project_env, run_puppy):
    """Ensure RGBA info isn't stripped if converting from a format like WebP."""
    # Create a transparent WebP
    img = Image.new('RGBA', (128, 128), (255, 0, 0, 128))
    icon_path = project_env['source'] / 'transparent.webp'
    img.save(icon_path, format='WEBP')

    (project_env['source'] / 'puppy.yaml').write_text("icon: 'transparent.webp'")

    run_puppy('push', '-n')

    staged_icon = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'icon.png'
    with Image.open(staged_icon) as v_img:
        assert v_img.mode == 'RGBA'
