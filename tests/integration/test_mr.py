import yaml
import pytest

pytestmark = pytest.mark.integration


def test_pack_lifecycle(mr_auth, make_home, inject_slug, run_cli, mr_api):
    home, project_dir = make_home('pack', {'modrinth': mr_auth['modrinth']})
    slug = inject_slug(project_dir, 'pack')

    # Step 4: create registers the project slot and writes id/slug to config
    run_cli(project_dir, 'create', '--site', 'modrinth')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('modrinth', {}).get('id'), 'modrinth.id not set after create'
    assert config['modrinth'].get('slug') == slug

    # Step 5: verify metadata sent during create (not push — body/icon/gallery tested in step 8)
    project_id = config['modrinth']['id']
    mr_data = mr_api(f'/project/{project_id}')
    assert mr_data['title'] == config['name'], f'title mismatch: {mr_data["title"]!r}'
    assert mr_data['description'] == 'A minimal resource pack for puppy integration testing.'
    assert set(mr_data.get('categories', [])) >= {'blocks', 'environment', 'simplistic'}
    assert '16x' in (mr_data.get('additional_categories') or [])

    # Step 6: pull round-trips id/slug
    run_cli(project_dir, 'pull', '--site', 'modrinth')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['modrinth'].get('id'), 'modrinth.id missing after pull'
    assert config['modrinth'].get('slug') == slug


def test_mod_lifecycle(mr_auth, make_home, inject_slug, run_cli, mr_api):
    home, project_dir = make_home('mod', {'modrinth': mr_auth['modrinth']})
    slug = inject_slug(project_dir, 'mod')

    # Step 4: create registers the project slot and writes id/slug to config
    run_cli(project_dir, 'create', '--site', 'modrinth')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('modrinth', {}).get('id'), 'modrinth.id not set after create'
    assert config['modrinth'].get('slug') == slug

    # Step 5: verify metadata sent during create (not push — body/icon/gallery tested in step 8)
    project_id = config['modrinth']['id']
    mr_data = mr_api(f'/project/{project_id}')
    assert mr_data['title'] == config['name'], f'title mismatch: {mr_data["title"]!r}'
    assert mr_data['description'] == 'A minimal Fabric mod for puppy integration testing.'
    assert set(mr_data.get('categories', [])) >= {'utility', 'library'}

    # Step 6: pull round-trips id/slug
    run_cli(project_dir, 'pull', '--site', 'modrinth')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['modrinth'].get('id'), 'modrinth.id missing after pull'
    assert config['modrinth'].get('slug') == slug
