import yaml
import pytest

from puppy.config import ConfigSynthesizer
from puppy.init import run_init


# ── common pack baseline ──────────────────────────────────────────────────────

def test_init_puppy_yaml_valid_yaml(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    content = (tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text()
    parsed = yaml.safe_load(content)
    assert isinstance(parsed, dict), 'puppy.yaml did not parse as a dict'


def test_init_uses_handle_not_pack(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    content = (tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text()
    parsed = yaml.safe_load(content)
    assert 'handle' in parsed
    assert 'pack' not in parsed


def test_init_handle_value_matches_directory(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert parsed['handle'] == 'mypack'


def test_init_name_derived_from_directory(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert parsed['name'] == 'Mypack'


def test_init_has_summary_field(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert 'summary' in parsed


def test_init_links_does_not_contain_social_keys(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    links = parsed.get('links') or {}
    assert 'discord' not in links


def test_init_has_socials_block(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert 'socials' in parsed


def test_init_creates_required_files(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    home = tmp_path / 'mypack' / 'puppy'
    assert (home / 'puppy.yaml').exists()
    assert (home / 'auth.yaml').exists()
    assert (home / '.gitignore').exists()
    assert (home / 'description.md').exists()


def test_init_gitignore_covers_auth(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    content = (tmp_path / 'mypack' / 'puppy' / '.gitignore').read_text()
    assert 'auth.yaml' in content


def test_init_config_loads_without_errors(tmp_path):
    project_dir = tmp_path / 'mypack'
    run_init(project_dir, 'pack')
    puppy_home = project_dir / 'puppy'
    config = ConfigSynthesizer(puppy_home, project_dir).get_running_config()
    assert config.get('name') == 'Mypack'
    assert config.get('handle') == 'mypack'


# ── type field ────────────────────────────────────────────────────────────────

def test_init_pack_sets_type(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    parsed = yaml.safe_load((tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text())
    assert parsed['type'] == 'pack'


def test_init_mod_sets_type(tmp_path):
    run_init(tmp_path / 'mymod', 'mod')
    parsed = yaml.safe_load((tmp_path / 'mymod' / 'puppy' / 'puppy.yaml').read_text())
    assert parsed['type'] == 'mod'


def test_init_world_sets_type(tmp_path):
    run_init(tmp_path / 'myworld', 'world')
    parsed = yaml.safe_load((tmp_path / 'myworld' / 'puppy' / 'puppy.yaml').read_text())
    assert parsed['type'] == 'world'


def test_init_unknown_type_raises(tmp_path):
    with pytest.raises(SystemExit, match='Unknown project type'):
        run_init(tmp_path / 'mypack', 'datapack')


# ── type-specific neutral fields ──────────────────────────────────────────────

def test_init_pack_has_resolution(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    content = (tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text()
    assert 'resolution:' in content


def test_init_pack_has_progress(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    content = (tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text()
    assert 'progress:' in content


def test_init_mod_has_loaders(tmp_path):
    run_init(tmp_path / 'mymod', 'mod')
    content = (tmp_path / 'mymod' / 'puppy' / 'puppy.yaml').read_text()
    assert 'loaders:' in content


def test_init_mod_has_no_resolution(tmp_path):
    run_init(tmp_path / 'mymod', 'mod')
    content = (tmp_path / 'mymod' / 'puppy' / 'puppy.yaml').read_text()
    assert 'resolution:' not in content


def test_init_world_has_progress(tmp_path):
    run_init(tmp_path / 'myworld', 'world')
    content = (tmp_path / 'myworld' / 'puppy' / 'puppy.yaml').read_text()
    assert 'progress:' in content


def test_init_world_has_no_resolution(tmp_path):
    run_init(tmp_path / 'myworld', 'world')
    content = (tmp_path / 'myworld' / 'puppy' / 'puppy.yaml').read_text()
    assert 'resolution:' not in content


# ── site filtering ────────────────────────────────────────────────────────────

def test_init_pack_includes_all_sites(tmp_path):
    run_init(tmp_path / 'mypack', 'pack')
    content = (tmp_path / 'mypack' / 'puppy' / 'puppy.yaml').read_text()
    assert 'curseforge:' in content
    assert 'modrinth:' in content
    assert 'planetminecraft:' in content


def test_init_mod_includes_all_three(tmp_path):
    # PMC now hosts mods too, so the mod skeleton includes all three sites
    run_init(tmp_path / 'mymod', 'mod')
    content = (tmp_path / 'mymod' / 'puppy' / 'puppy.yaml').read_text()
    assert 'curseforge:' in content
    assert 'modrinth:' in content
    assert 'planetminecraft:' in content


def test_init_world_excludes_modrinth(tmp_path):
    run_init(tmp_path / 'myworld', 'world')
    content = (tmp_path / 'myworld' / 'puppy' / 'puppy.yaml').read_text()
    assert 'curseforge:' in content
    assert 'planetminecraft:' in content
    assert 'modrinth:' not in content
