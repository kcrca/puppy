import yaml
import pytest

pytestmark = pytest.mark.integration


def test_pack_lifecycle(cf_auth, make_home, inject_slug, run_cli, cf_api):
    home, project_dir = make_home('pack', {'curseforge': cf_auth['curseforge']})
    slug = inject_slug(project_dir, 'pack')

    # Step 4: create registers the project slot and writes id/slug to config
    run_cli(project_dir, 'create', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('curseforge', {}).get('id'), 'curseforge.id not set after create'

    # Step 5: verify metadata sent during create (not push — description body/gallery tested in step 8)
    project_id = config['curseforge']['id']
    cf_data = cf_api(f'/projects/{project_id}')
    assert cf_data.get('name', '').startswith('Puppy Test Pack'), f'name mismatch: {cf_data.get("name")!r}'
    assert cf_data.get('summary') == 'A minimal resource pack for puppy integration testing.'
    assert cf_data.get('primaryCategoryId') == 393

    # Step 6: pull round-trips id/slug
    run_cli(project_dir, 'pull', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['curseforge'].get('id'), 'curseforge.id missing after pull'
    assert config['curseforge'].get('slug'), 'curseforge.slug missing after pull'


def test_world_lifecycle(cf_auth, make_home, inject_slug, run_cli, cf_api):
    home, project_dir = make_home('world', {'curseforge': cf_auth['curseforge']})
    slug = inject_slug(project_dir, 'world')

    # Step 4: create registers the project slot and writes id/slug to config
    run_cli(project_dir, 'create', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('curseforge', {}).get('id'), 'curseforge.id not set after create'

    # Step 5: verify metadata sent during create (not push — description body/gallery tested in step 8)
    project_id = config['curseforge']['id']
    cf_data = cf_api(f'/projects/{project_id}')
    assert cf_data.get('name', '').startswith('Puppy Test World'), f'name mismatch: {cf_data.get("name")!r}'
    assert cf_data.get('summary') == 'A minimal world save for puppy integration testing.'
    assert cf_data.get('primaryCategoryId') == 253

    # Step 6: pull round-trips id/slug
    run_cli(project_dir, 'pull', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['curseforge'].get('id'), 'curseforge.id missing after pull'
    assert config['curseforge'].get('slug'), 'curseforge.slug missing after pull'
