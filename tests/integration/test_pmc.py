import yaml
import pytest

pytestmark = pytest.mark.integration


def test_pack_lifecycle(pmc_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('pack', {'planetminecraft': pmc_auth['planetminecraft']})
    slug = inject_slug(project_dir, 'pack')

    run_cli(project_dir, 'create', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('planetminecraft', {}).get('id'), 'planetminecraft.id not set after create'

    # Step 6: pull and verify harvested fields
    run_cli(project_dir, 'pull', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['planetminecraft'].get('id'), 'planetminecraft.id missing after pull'
    assert config['planetminecraft'].get('slug'), 'planetminecraft.slug missing after pull'
    assert config.get('name'), 'name not harvested after pull'


def test_world_lifecycle(pmc_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('world', {'planetminecraft': pmc_auth['planetminecraft']})
    slug = inject_slug(project_dir, 'world')

    run_cli(project_dir, 'create', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('planetminecraft', {}).get('id'), 'planetminecraft.id not set after create'

    # Step 6: pull and verify harvested fields
    run_cli(project_dir, 'pull', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['planetminecraft'].get('id'), 'planetminecraft.id missing after pull'
    assert config['planetminecraft'].get('slug'), 'planetminecraft.slug missing after pull'
    assert config.get('name'), 'name not harvested after pull'
