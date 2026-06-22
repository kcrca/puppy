import pytest
import yaml
import tempfile
from pathlib import Path

from puppy.renderer import render
from puppy.sites import MODRINTH, CURSEFORGE


def test_site_block_shadows_neutral_variable():
    # the current site's block overrides a neutral top-level var during render
    config = {'like': 'follow', 'curseforge': {'like': 'click follow'}, 'modrinth': {}}
    assert 'please click follow' in render('please {{ like }}', config, site=CURSEFORGE)
    # a site without its own value falls back to the neutral top-level one
    assert 'please follow' in render('please {{ like }}', config, site=MODRINTH)


def test_site_dir_key_outranks_block():
    # a key set by a site-dir puppy.yaml (recorded in _site_dir_keys) is more
    # specific than the inline block, so the block does not shadow it
    config = {'val': 'sitedir', 'curseforge': {'val': 'block'}, '_site_dir_keys': {'val'}}
    assert 'val=sitedir' in render('val={{ val }}', config, site=CURSEFORGE)


def test_site_block_dict_merge_keeps_other_keys():
    # dict values merge one level deep, so a partial override keeps the rest
    config = {
        'links': {'home': 'H', 'source': 'S'},
        'curseforge': {'links': {'source': 'CF_S'}},
    }
    out = render('{{ links.home }}|{{ links.source }}', config, site=CURSEFORGE)
    assert 'H|CF_S' in out


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
        'projects': {'other': {'modrinth': {'url': 'https://modrinth.com/resourcepack/other'}}},
        'other_url': '{{ projects.other.url }}',
        'blurb': 'See {{ other_url }} for details.',
    }
    result = render('{{ blurb }}', config, site=MODRINTH)
    assert result == 'See https://modrinth.com/resourcepack/other for details.'


def test_config_string_direct_project_ref():
    config = {
        'projects': {'other': {'modrinth': {'url': 'https://modrinth.com/resourcepack/other'}}},
        'link': '[Other]({{ projects.other.url }})',
    }
    result = render('{{ link }}', config, site=MODRINTH)
    assert result == '[Other](https://modrinth.com/resourcepack/other)'


def test_unknown_variable_raises():
    with pytest.raises(SystemExit, match='no_such_var'):
        render('{{ no_such_var }}', {})


def test_unknown_variable_in_config_string_raises():
    with pytest.raises(SystemExit, match='no_such_var'):
        render('{{ x }}', {'x': '{{ no_such_var }}'})


def test_unknown_variable_in_if_is_falsy():
    result = render('{% if no_such_var %}yes{% else %}no{% endif %}', {})
    assert result == 'no'


def test_read_function_inlines_file(tmp_path):
    target = tmp_path / 'credits.md'
    target.write_text('Thanks everyone!')
    result = render(f'{{{{ read("{target}") }}}}', {})
    assert result == 'Thanks everyone!'


def test_read_function_with_path_variable(tmp_path):
    target = tmp_path / 'notes.md'
    target.write_text('Some notes.')
    result = render('{{ read(top + "/notes.md") }}', {'top': str(tmp_path)})
    assert result == 'Some notes.'


def test_read_function_missing_file_raises(tmp_path):
    with pytest.raises(Exception):
        render(f'{{{{ read("{tmp_path}/nonexistent.md") }}}}', {})


def test_read_function_with_project_variable(project_env, run_puppy, tmp_path):
    notes = Path(project_env['project']) / 'notes.md'
    notes.write_text('Project notes here.')
    (project_env['project'] / 'description.md').write_text('{{ read(project + "/notes.md") }}')
    run_puppy('push', '-n', '-s', 'modrinth')
    out = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md'
    assert 'Project notes here.' in out.read_text()


def test_config_string_deep_chain_expansion():
    # chain: v0 -> v1 -> v2 -> ... -> v19 -> 'final'
    n = 20
    config = {f'v{i}': f'{{{{ v{i + 1} }}}}' for i in range(n - 1)}
    config[f'v{n - 1}'] = 'final'
    result = render('{{ v0 }}', config)
    assert result == 'final'
