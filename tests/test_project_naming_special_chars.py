import os
import tempfile
import yaml
from pathlib import Path


def test_project_name_with_spaces_and_special_chars(project_env, run_puppy):
    """Spec 2: Preserves casing and special characters in 'name'."""
    (project_env['source'] / 'puppy.yaml').write_text(
        yaml.dump({'name': 'Neon Glow!', 'status': 'online'})
    )
    (project_env['source'] / 'description.md').write_text('Welcome to {{ name }}.')

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_root = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow'
    mr_meta = yaml.safe_load((debug_root / 'modrinth' / 'metadata.yaml').read_text())
    assert mr_meta['name'] == 'Neon Glow!'

    content = (debug_root / 'modrinth' / 'description.md').read_text()
    assert 'Welcome to Neon Glow!.' in content


def test_auto_derived_name_from_directory_with_special_chars(project_env, run_puppy):
    """Verifies that if the directory itself has special chars, Puppy derives slug correctly."""
    special_dir = project_env['home'] / 'Cool Pack!'
    (special_dir / 'puppy').mkdir(parents=True)
    (special_dir / 'puppy' / 'description.md').write_text('Name: {{ name }}')

    os.chdir(special_dir)
    run_puppy('push', '-n', '-s', 'modrinth')

    debug_root = Path(tempfile.gettempdir()) / 'puppy' / 'coolpack'
    content = (debug_root / 'modrinth' / 'description.md').read_text()
    assert 'Name: Cool Pack!' in content
