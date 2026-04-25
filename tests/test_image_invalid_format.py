import pytest


def test_invalid_file_raises_error(project_env, run_puppy):
    """Pillow's UnidentifiedImageError should be caught and lead to a fatal exit."""
    # A text file renamed to .png or .jpg
    bad_icon = project_env['project'] / 'fake_image.png'
    bad_icon.write_text('This is definitely not a header Pillow recognizes.')

    (project_env['project'] / 'puppy.yaml').write_text("icon: 'fake_image.png'")

    # Puppy should catch the UnidentifiedImageError and exit(1)
    exit_code = run_puppy('push', '-n')
    assert exit_code != 0
