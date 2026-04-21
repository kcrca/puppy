import yaml
import tempfile
from pathlib import Path


def test_sibling_project_url_injection(project_env, run_puppy):
    """Verify that sibling projects are scanned and their URLs injected into Jinja."""
    # Create a sibling project 'emerald'
    emerald_root = project_env['home'] / 'Emerald'
    (emerald_root / 'puppy').mkdir(parents=True)
    (emerald_root / 'puppy' / 'puppy.yaml').write_text(
        "pack: 'emerald'\nmodrinth:\n  slug: 'emerald-pack'\n  type: 'resourcepack'"
    )

    # Update global config to include both projects
    (project_env['home'] / 'puppy.yaml').write_text(
        'projects:\n  - NeonGlow\n  - Emerald'
    )

    # Use the link in NeonGlow's description
    (project_env['source'] / 'description.md').write_text(
        'Check out {{ projects.emerald.modrinth.url }}'
    )

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'modrinth'
        / 'description.md'
    )
    # Should resolve to modrinth.com/{type}/{slug}
    assert 'https://modrinth.com/resourcepack/emerald-pack' in debug_file.read_text()
