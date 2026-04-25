import tempfile
import yaml
from pathlib import Path


def test_slug_sanitization_rules(project_env, run_puppy):
    """Ensures that 'Neon Glow!' generates a clean slug for folders."""
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'name': 'Neon Glow!'}))

    run_puppy('push', '-n', '-s', 'modrinth')

    temp_root = Path(tempfile.gettempdir()) / 'puppy'
    possible_slugs = ['neonglow', 'neon-glow']
    assert any((temp_root / slug).exists() for slug in possible_slugs)

    actual_slug = 'neonglow' if (temp_root / 'neonglow').exists() else 'neon-glow'
    meta = yaml.safe_load((temp_root / actual_slug / 'modrinth' / 'metadata.yaml').read_text())
    assert meta['name'] == 'Neon Glow!'
