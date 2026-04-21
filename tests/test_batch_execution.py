import tempfile
from pathlib import Path
import os


def test_multi_pack_batch_staging(project_env, run_puppy):
    """
    In batch mode (projects: [A, B]), Puppy must iterate through each project.
    Verifies that the debug root contains a folder for every project in the list.
    """
    # Create sibling project 'Alpha'
    alpha_root = project_env['home'] / 'Alpha'
    (alpha_root / 'puppy').mkdir(parents=True)
    (alpha_root / 'puppy' / 'puppy.yaml').write_text('name: Alpha')

    # Update global config to list both
    (project_env['home'] / 'puppy.yaml').write_text('projects: [NeonGlow, Alpha]')

    # Run from the global root
    os.chdir(project_env['root'])
    run_puppy('push', '-n')

    temp_root = Path(tempfile.gettempdir()) / 'puppy'

    # Check that both packs were staged in the same run
    assert (temp_root / 'neonglow').exists()
    assert (temp_root / 'alpha').exists()
