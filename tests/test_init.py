import yaml
import pytest

from puppy.config import ConfigSynthesizer
from puppy.init import run_init


def test_init_puppy_yaml_valid_yaml(tmp_path):
    run_init(tmp_path / 'mypack')
    content = (tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text()
    parsed = yaml.safe_load(content)
    assert isinstance(parsed, dict), 'puppy.yaml did not parse as a dict'


def test_init_uses_handle_not_pack(tmp_path):
    run_init(tmp_path / 'mypack')
    content = (tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text()
    parsed = yaml.safe_load(content)
    assert 'handle' in parsed, "'handle' key missing from generated puppy.yaml"
    assert 'pack' not in parsed, "obsolete 'pack' key present in generated puppy.yaml"


def test_init_handle_value_matches_directory(tmp_path):
    run_init(tmp_path / 'mypack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert parsed['handle'] == 'mypack'


def test_init_name_derived_from_directory(tmp_path):
    run_init(tmp_path / 'mypack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert parsed['name'] == 'Mypack'


def test_init_has_summary_field(tmp_path):
    run_init(tmp_path / 'mypack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert 'summary' in parsed, "'summary' key missing from generated puppy.yaml"


def test_init_links_does_not_contain_social_keys(tmp_path):
    run_init(tmp_path / 'mypack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    links = parsed.get('links') or {}
    assert 'discord' not in links, "'discord' should be under 'socials', not 'links'"


def test_init_has_socials_block(tmp_path):
    run_init(tmp_path / 'mypack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert 'socials' in parsed, "'socials' block missing from generated puppy.yaml"


def test_init_creates_required_files(tmp_path):
    run_init(tmp_path / 'mypack')
    home = tmp_path / 'mypack' / 'puppy'
    assert (home / 'puppy.yaml').exists()
    assert (home / 'auth.yaml').exists()
    assert (home / '.gitignore').exists()
    assert (home / 'description.md').exists()


def test_init_gitignore_covers_auth(tmp_path):
    run_init(tmp_path / 'mypack')
    content = (tmp_path / 'mypack' / 'puppy' / '.gitignore').read_text()
    assert 'auth.yaml' in content


def test_init_config_loads_without_errors(tmp_path):
    project_dir = tmp_path / 'mypack'
    run_init(project_dir)
    puppy_home = project_dir / 'puppy'
    config = ConfigSynthesizer(puppy_home, project_dir).get_running_config()
    assert config.get('name') == 'Mypack'
    assert config.get('handle') == 'mypack'
