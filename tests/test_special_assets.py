from PIL import Image
import tempfile
from pathlib import Path


def test_thumbnail_and_logo_staging(project_env, run_puppy):
    """thumbnail.png and logo.png should be staged separately from general icons."""
    (project_env['source'] / 'thumbnail.png').write_text('fake_thumb')
    (project_env['source'] / 'logo.png').write_text('fake_logo')
    # Also include a normal icon
    img = Image.new('RGB', (64, 64))
    img.save(project_env['source'] / 'icon.png')

    run_puppy('push', '-n')

    temp_root = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow'
    assert (temp_root / 'icon.png').exists()
