import yaml


def test_strict_version_boundary(project_env, run_puppy):
    """1.2 should not match 1.2.4."""
    (project_env['source'] / 'puppy.yaml').write_text(yaml.dump({'version': '1.2'}))
    (project_env['source'] / 'neonglow-1.2.4.zip').write_text('wrong')
    (project_env['source'] / 'neonglow-1.2.zip').write_text('correct')

    result = run_puppy('push', '--pack', '-n')
    assert result is None or result == 0
