import tempfile
import yaml
from pathlib import Path


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
