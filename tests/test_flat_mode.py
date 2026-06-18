import os
import tempfile
import yaml
from pathlib import Path


def test_flat_project_inference(tmp_path, run_puppy):
    """In flat mode, puppy.yaml in the home dir should trigger a single-project run."""
    home = tmp_path / 'simple_pack' / 'puppy'
    home.mkdir(parents=True)

    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'auth.yaml').write_text(yaml.dump({
        'modrinth': 'token',
        'curseforge': {'token': 'tok', 'cookie': 'CobaltSession=x'},
        'planetminecraft': 'pmc_autologin=x',
    }))
    (home / 'puppy.yaml').write_text(yaml.dump({'name': 'SimplePack', 'version': '1.0', 'type': 'pack'}))
    (home / 'description.md').write_text('Flat mode content')

    os.chdir(home.parent)
    run_puppy('push', '-n')

    debug_dir = Path(tempfile.gettempdir()).resolve() / 'puppy' / 'simplepack'
    assert debug_dir.exists()
    assert 'Flat mode content' in (debug_dir / 'modrinth' / 'description.md').read_text()
