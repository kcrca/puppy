import tempfile
import yaml
from pathlib import Path


def test_batch_index_shows_correct_zip_per_project(project_env, run_puppy):
    """In batch mode with --pack, each project's index.html should link to its own zip."""
    (project_env['source'] / 'neonglow-1.0.zip').write_text('neon_data')
    (project_env['source'] / 'puppy.yaml').write_text(
        yaml.dump({'version': '1.0', 'minecraft': '1.20'})
    )

    alpha = project_env['home'] / 'Alpha'
    (alpha / 'puppy').mkdir(parents=True)
    (alpha / 'puppy' / 'puppy.yaml').write_text(
        yaml.dump({'name': 'Alpha', 'version': '1.0', 'minecraft': '1.20'})
    )
    (alpha / 'puppy' / 'alpha-1.0.zip').write_text('alpha_data')

    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow', 'Alpha']}))

    run_puppy('push', '-n', '--pack', '-d', str(project_env['home']))

    temp_root = Path(tempfile.gettempdir()) / 'puppy'

    neon_index = (temp_root / 'neonglow' / 'index.html').read_text()
    assert 'neonglow-1.0.zip' in neon_index
    assert (temp_root / 'neonglow' / 'neonglow-1.0.zip').exists()

    alpha_index = (temp_root / 'alpha' / 'index.html').read_text()
    assert 'alpha-1.0.zip' in alpha_index
    assert (temp_root / 'alpha' / 'alpha-1.0.zip').exists()
