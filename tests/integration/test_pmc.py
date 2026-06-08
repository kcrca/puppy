import yaml
import pytest

pytestmark = pytest.mark.integration


def test_pack_lifecycle(pmc_auth, make_home, inject_slug, run_cli, pmc_page):
    home, project_dir = make_home('pack', {'planetminecraft': pmc_auth['planetminecraft']})
    slug = inject_slug(project_dir, 'pack')

    # Step 4: create registers the project slot and writes id/slug to config
    run_cli(project_dir, 'create', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('planetminecraft', {}).get('id'), 'planetminecraft.id not set after create'
    assert config['planetminecraft'].get('slug'), 'planetminecraft.slug not set after create'

    # Step 5: verify title visible in management page (public page held for moderation)
    project_id = config['planetminecraft']['id']
    html = pmc_page(f'https://www.planetminecraft.com/account/manage/texture-packs/{project_id}/')
    assert 'Puppy Test Pack' in html, 'project name not found in PMC management page'

    # Step 6: pull round-trips id/slug
    run_cli(project_dir, 'pull', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['planetminecraft'].get('id'), 'planetminecraft.id missing after pull'
    assert config['planetminecraft'].get('slug'), 'planetminecraft.slug missing after pull'


def test_world_lifecycle(pmc_auth, make_home, inject_slug, run_cli, pmc_page):
    home, project_dir = make_home('world', {'planetminecraft': pmc_auth['planetminecraft']})
    slug = inject_slug(project_dir, 'world')

    # Step 4: create registers the project slot and writes id/slug to config
    run_cli(project_dir, 'create', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('planetminecraft', {}).get('id'), 'planetminecraft.id not set after create'
    assert config['planetminecraft'].get('slug'), 'planetminecraft.slug not set after create'

    # Step 5: verify title visible in management page
    project_id = config['planetminecraft']['id']
    html = pmc_page(f'https://www.planetminecraft.com/account/manage/projects/{project_id}/')
    assert 'Puppy Test World' in html, 'project name not found in PMC management page'

    # Step 6: pull round-trips id/slug
    run_cli(project_dir, 'pull', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['planetminecraft'].get('id'), 'planetminecraft.id missing after pull'
    assert config['planetminecraft'].get('slug'), 'planetminecraft.slug missing after pull'
