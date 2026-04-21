import os
import tempfile
from pathlib import Path


def test_flat_project_inference(tmp_path, run_puppy):
    """In flat mode, puppy.yaml in the home dir should trigger a single-project run."""
    home = tmp_path / 'simple_pack' / 'puppy'
    home.mkdir(parents=True)

    # Security files
    (home / '.gitignore').write_text('auth.yaml')
    (home / 'auth.yaml').write_text('modrinth: token')

    # Config in home dir instead of project subdir
    (home / 'puppy.yaml').write_text("name: SimplePack\nversion: '1.0'")
    (home / 'description.md').write_text('Flat mode content')

    # Run from the parent of puppy/
    os.chdir(home.parent)
    run_puppy('push', '-n')

    debug_dir = Path(tempfile.gettempdir()) / 'puppy' / 'simplepack'
    assert debug_dir.exists()
    assert (
        'Flat mode content' in (debug_dir / 'modrinth' / 'description.md').read_text()
    )
