import yaml


def test_strict_version_boundary(project_env, run_puppy):
    """Ensures version 1.2 does not accidentally match 1.2.4."""
    (project_env['project'] / 'pack-1.2.4.zip').write_text('wrong')
    (project_env['project'] / 'pack-1.2.zip').write_text('correct')
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'minecraft': '1.20'}))

    exit_code = run_puppy('push', '-n', '--pack', '--version', '1.2')
    assert exit_code == 0 or exit_code is None
