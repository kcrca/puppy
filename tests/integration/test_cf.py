import yaml
import pytest

pytestmark = pytest.mark.integration


def test_pack_lifecycle(cf_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('pack', {'curseforge': cf_auth['curseforge']})
    slug = inject_slug(project_dir, 'pack')

    run_cli(project_dir, 'create', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('curseforge', {}).get('id'), 'curseforge.id not set after create'

    # Step 6: pull and verify harvested fields
    run_cli(project_dir, 'pull', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['curseforge'].get('id'), 'curseforge.id missing after pull'
    assert config['curseforge'].get('slug'), 'curseforge.slug missing after pull'
    assert config.get('name'), 'name not harvested after pull'
    assert config.get('summary'), 'summary not harvested after pull'
    assert config['curseforge'].get('category'), 'category not harvested after pull'


def test_world_lifecycle(cf_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('world', {'curseforge': cf_auth['curseforge']})
    slug = inject_slug(project_dir, 'world')

    run_cli(project_dir, 'create', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('curseforge', {}).get('id'), 'curseforge.id not set after create'

    # Step 6: pull and verify harvested fields
    run_cli(project_dir, 'pull', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['curseforge'].get('id'), 'curseforge.id missing after pull'
    assert config['curseforge'].get('slug'), 'curseforge.slug missing after pull'
    assert config.get('name'), 'name not harvested after pull'
    assert config.get('summary'), 'summary not harvested after pull'
    assert config['curseforge'].get('category'), 'category not harvested after pull'
