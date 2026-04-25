import tempfile
import yaml
from pathlib import Path


def test_batch_site_filter_isolation(project_env, run_puppy):
    """Running 'puppy push -n -s modrinth' in batch mode should only stage Modrinth content."""
    other = project_env['home'] / 'Other'
    other.mkdir(parents=True)
    (other / 'puppy.yaml').write_text(yaml.dump({'name': 'Other'}))
    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'projects': ['NeonGlow', 'Other']}))

    run_puppy('push', '-n', '-s', 'modrinth', '-d', str(project_env['home']))

    temp_root = Path(tempfile.gettempdir()) / 'puppy'
    for pack in ['neonglow', 'other']:
        index = (temp_root / pack / 'index.html').read_text()
        assert 'Modrinth' in index
        assert 'CurseForge' not in index
        assert 'Planet Minecraft' not in index
