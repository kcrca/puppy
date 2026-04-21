import tempfile
from pathlib import Path


def test_batch_index_shows_correct_zip_per_project(project_env, run_puppy):
    """
    In batch mode with --pack, each project's index.html should link to
    its own specific zip file.
    """
    # Setup NeonGlow zip
    (project_env['source'] / 'neonglow-1.0.zip').write_text('neon_data')
    (project_env['source'] / 'puppy.yaml').write_text(
        "version: '1.0'\nminecraft: '1.20'"
    )

    # Setup Alpha zip
    alpha = project_env['home'] / 'Alpha'
    (alpha / 'puppy').mkdir(parents=True)
    (alpha / 'puppy' / 'puppy.yaml').write_text(
        "name: Alpha\nversion: '1.0'\nminecraft: '1.20'"
    )
    (alpha / 'puppy' / 'alpha-1.0.zip').write_text('alpha_data')

    (project_env['home'] / 'puppy.yaml').write_text('projects: [NeonGlow, Alpha]')

    run_puppy('push', '-n', '--pack', '-d', str(project_env['home']))

    temp_root = Path(tempfile.gettempdir()) / 'puppy'

    # NeonGlow index should link to neonglow-1.0.zip
    neon_index = (temp_root / 'neonglow' / 'index.html').read_text()
    assert 'neonglow-1.0.zip' in neon_index
    assert (temp_root / 'neonglow' / 'neonglow-1.0.zip').exists()

    # Alpha index should link to alpha-1.0.zip
    alpha_index = (temp_root / 'alpha' / 'index.html').read_text()
    assert 'alpha-1.0.zip' in alpha_index
    assert (temp_root / 'alpha' / 'alpha-1.0.zip').exists()
