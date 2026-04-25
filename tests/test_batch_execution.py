import tempfile
import os
import yaml
from pathlib import Path


def test_multi_pack_batch_staging(project_env, run_puppy):
    """In batch mode (projects: [A, B]), Puppy must iterate through each project."""
    alpha_root = project_env['home'] / 'Alpha'
    alpha_root.mkdir(parents=True)
    (alpha_root / 'puppy.yaml').write_text(yaml.dump({'name': 'Alpha'}))

    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow', 'Alpha']}))

    os.chdir(project_env['root'])
    run_puppy('push', '-n')

    temp_root = Path(tempfile.gettempdir()) / 'puppy'
    assert (temp_root / 'neonglow').exists()
    assert (temp_root / 'alpha').exists()
