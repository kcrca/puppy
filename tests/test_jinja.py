import pytest
import yaml
import tempfile
from pathlib import Path

from jinja2 import UndefinedError

from puppy.renderer import render
from puppy.sites import MODRINTH


def test_all_yaml_vars_available_to_jinja(project_env, run_puppy):
    config = {'minecraft': '1.20.1', 'custom': {'val': 'hello'}}
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump(config))
    (project_env['project'] / 'description.md').write_text(
        'MC: {{ minecraft }}, Val: {{ custom.val }}'
    )

    run_puppy('push', '-n')

    debug_file = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'modrinth'
        / 'description.md'
    )
    content = debug_file.read_text()

    assert 'MC: 1.20.1' in content
    assert 'Val: hello' in content


def test_config_string_values_expanded_recursively():
    config = {
        'projects': {'other': {'modrinth': {'url': 'https://modrinth.com/mod/other'}}},
        'other_url': '{{ projects.other.url }}',
        'blurb': 'See {{ other_url }} for details.',
    }
    result = render('{{ blurb }}', config, site=MODRINTH)
    assert result == 'See https://modrinth.com/mod/other for details.'


def test_config_string_direct_project_ref():
    config = {
        'projects': {'other': {'modrinth': {'url': 'https://modrinth.com/mod/other'}}},
        'link': '[Other]({{ projects.other.url }})',
    }
    result = render('{{ link }}', config, site=MODRINTH)
    assert result == '[Other](https://modrinth.com/mod/other)'


def test_unknown_variable_raises():
    with pytest.raises(UndefinedError):
        render('{{ no_such_var }}', {})


def test_unknown_variable_in_config_string_raises():
    with pytest.raises(UndefinedError):
        render('{{ x }}', {'x': '{{ no_such_var }}'})


def test_unknown_variable_in_if_is_falsy():
    result = render('{% if no_such_var %}yes{% else %}no{% endif %}', {})
    assert result == 'no'


def test_config_string_deep_chain_expansion():
    # chain: v0 -> v1 -> v2 -> ... -> v19 -> 'final'
    n = 20
    config = {f'v{i}': f'{{{{ v{i + 1} }}}}' for i in range(n - 1)}
    config[f'v{n - 1}'] = 'final'
    result = render('{{ v0 }}', config)
    assert result == 'final'
