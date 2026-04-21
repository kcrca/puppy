import tempfile
import yaml
from pathlib import Path


def test_variables_do_not_leak_between_projects(project_env, run_puppy):
    """Variables defined in Project A's puppy.yaml should not be visible to Project B."""
    (project_env['source'] / 'puppy.yaml').write_text(yaml.dump({'secret_val': 'neon'}))
    (project_env['source'] / 'description.md').write_text('Val: {{ secret_val }}')

    alpha = project_env['home'] / 'Alpha'
    (alpha / 'puppy').mkdir(parents=True)
    (alpha / 'puppy' / 'puppy.yaml').write_text(yaml.dump({'name': 'Alpha'}))
    (alpha / 'puppy' / 'description.md').write_text('Val: {{ secret_val }}')

    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow', 'Alpha']}))

    run_puppy('push', '-n', '-d', str(project_env['home']))

    temp_root = Path(tempfile.gettempdir()) / 'puppy'
    assert 'Val: neon' in (temp_root / 'neonglow' / 'modrinth' / 'description.md').read_text()
    assert '{{ secret_val }}' in (temp_root / 'alpha' / 'modrinth' / 'description.md').read_text()
