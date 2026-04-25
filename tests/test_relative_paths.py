import yaml


def test_relative_path_resolution(project_env, run_puppy):
    """Relative paths should resolve relative to the project source directory."""
    ext_dir = project_env['root'] / 'external_assets'
    ext_dir.mkdir()
    (ext_dir / 'icon.png').write_text('external_icon')

    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'icon': '../external_assets/icon.png'})
    )

    result = run_puppy('push', '-n')
    assert result is None or result == 0
