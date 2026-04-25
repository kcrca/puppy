import shutil
import tempfile
import yaml
from pathlib import Path


def test_pack_filter_runs_only_named_pack(project_env, run_puppy):
    """puppy push <pack> runs only that pack in batch mode."""
    temp_root = Path(tempfile.gettempdir()) / 'puppy'
    for name in ('neonglow', 'filteronly'):
        if (temp_root / name).exists():
            shutil.rmtree(temp_root / name)

    alpha_root = project_env['home'] / 'Alpha'
    (alpha_root / 'puppy').mkdir(parents=True)
    (alpha_root / 'puppy' / 'puppy.yaml').write_text(yaml.dump({'name': 'Alpha', 'pack': 'filteronly'}))

    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow', 'Alpha']}))

    run_puppy('push', 'neonglow', '-n', '-d', str(project_env['home']))

    assert (temp_root / 'neonglow').exists()
    assert not (temp_root / 'filteronly').exists()


def test_pack_filter_unknown_pack_errors(project_env, run_puppy):
    """puppy push <unknown> exits with an error."""
    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow']}))

    result = run_puppy('push', 'nosuchpack', '-n', '-d', str(project_env['home']))
    assert 'nosuchpack' in str(result)
