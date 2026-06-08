import yaml
import pytest

pytestmark = pytest.mark.integration


def test_pack_lifecycle(mr_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('pack', {'modrinth': mr_auth['modrinth']})
    slug = inject_slug(project_dir, 'pack')

    run_cli(project_dir, 'create', '--site', 'modrinth')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('modrinth', {}).get('id'), 'modrinth.id not set after create'
    assert config['modrinth'].get('slug') == slug


def test_mod_lifecycle(mr_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('mod', {'modrinth': mr_auth['modrinth']})
    slug = inject_slug(project_dir, 'mod')

    run_cli(project_dir, 'create', '--site', 'modrinth')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('modrinth', {}).get('id'), 'modrinth.id not set after create'
    assert config['modrinth'].get('slug') == slug
