import tempfile
import yaml
from pathlib import Path


def test_variable_priority(project_env, run_puppy):
    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'val': 'global', 'type': 'pack'}))
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'val': 'project'}))
    (project_env['project'] / 'description.md').write_text('{{ val }}')

    run_puppy('push', '-n')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'project' in debug_file.read_text()


def test_site_dir_file_beats_inline_block(project_env, run_puppy):
    # site-dir > nested block > neutral: a value in modrinth/puppy.yaml outranks
    # the inline modrinth: block, which in turn outranks the neutral top-level value.
    (project_env['home'] / 'puppy.yaml').write_text(yaml.dump({'type': 'pack'}))
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'val': 'neutral', 'modrinth': {'val': 'block'}})
    )
    mr_dir = project_env['project'] / 'modrinth'
    mr_dir.mkdir()
    (mr_dir / 'puppy.yaml').write_text(yaml.dump({'val': 'sitedir'}))
    (project_env['project'] / 'description.md').write_text('{{ val }}')

    run_puppy('push', '-n', '-s', 'modrinth')

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    assert 'sitedir' in debug_file.read_text()
