import tempfile
import yaml
from pathlib import Path


def test_additive_dict_merge(project_env, run_puppy):
    """Dicts in puppy.yaml should merge additively across layers."""
    mr_global_dir = project_env['home'] / 'modrinth'
    mr_global_dir.mkdir()
    (mr_global_dir / 'puppy.yaml').write_text(yaml.dump({'modrinth': {'tags': {'tag1': True}}}))

    mr_proj_dir = project_env['project'] / 'modrinth'
    mr_proj_dir.mkdir()
    (mr_proj_dir / 'puppy.yaml').write_text(yaml.dump({'modrinth': {'tags': {'tag2': True}}}))

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_meta = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'metadata.yaml'
    meta = yaml.safe_load(debug_meta.read_text())

    assert meta['tags']['tag1'] is True
    assert meta['tags']['tag2'] is True
