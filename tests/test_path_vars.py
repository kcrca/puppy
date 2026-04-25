import tempfile
import yaml
from pathlib import Path


def test_top_and_puppy_expand_in_description(project_env, run_puppy):
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'pack': 'neonglow', 'name': 'NeonGlow'})
    )
    (project_env['project'] / 'description.md').write_text(
        'puppy={{ puppy }}, top={{ top }}'
    )

    run_puppy('push', '-n', '-d', str(project_env['project']))

    debug_file = (
        Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    )
    content = debug_file.read_text()
    assert str(project_env['home']) in content
    assert str(project_env['root']) in content


def test_top_used_in_yaml_config_value(project_env, run_puppy):
    icon_path = project_env['root'] / 'pack.png'
    icon_path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({'pack': 'neonglow', 'name': 'NeonGlow', 'icon': '{{top}}/pack.png'})
    )
    (project_env['project'] / 'description.md').write_text('hello')

    result = run_puppy('push', '-n', '-d', str(project_env['project']))
    assert result != 1
