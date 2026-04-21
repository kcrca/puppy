import tempfile
from pathlib import Path

import yaml


def test_global_site_override(project_env, run_puppy):
    """Global site-specific puppy.yaml should override global general puppy.yaml"""
    # Global General
    (project_env['home'] / 'puppy.yaml').write_text(
        "common_var: 'base'\nsite_var: 'base'"
    )
    # Global Site Override (Modrinth)
    mr_home = project_env['home'] / 'modrinth'
    mr_home.mkdir()
    (mr_home / 'puppy.yaml').write_text("site_var: 'overridden'")

    (project_env['source'] / 'description.md').write_text(
        '{{ common_var }} {{ site_var }}'
    )
    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'modrinth'
        / 'description.md'
    )
    assert 'base overridden' in debug_file.read_text()
