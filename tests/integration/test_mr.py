import shutil
import yaml
import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

_INTEGRATION_DIR = Path(__file__).parent
_UPDATED_SUMMARY = 'Updated summary for MR integration testing.'
_NEW_SENTENCE = 'Updated by integration test.'


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

    # Step 7: modify description + summary, push with images
    desc_file = project_dir / 'description.md'
    desc_file.write_text(desc_file.read_text() + f'\n{_NEW_SENTENCE}\n\n{{{{ img(\'img1\') }}}}\n')
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['summary'] = _UPDATED_SUMMARY
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'modrinth', '--images')

    # Step 8: validate updated page via authenticated API
    mr_data = mr_api(f'/project/{project_id}')
    assert _NEW_SENTENCE in (mr_data.get('body') or ''), 'new sentence not in body after push'
    assert mr_data.get('icon_url'), 'icon_url missing after push'
    gallery = mr_data.get('gallery') or []
    assert len(gallery) >= 1, 'gallery empty after push with images'

    # Step 9: pull with images — summary and images.yaml updated
    run_cli(project_dir, 'pull', '--site', 'modrinth', '--images')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('summary') == _UPDATED_SUMMARY, f'summary not updated after pull: {config.get("summary")!r}'
    images_yaml = project_dir / 'images' / 'images.yaml'
    assert images_yaml.exists(), 'images/images.yaml missing after pull --images'
    img_entries = yaml.safe_load(images_yaml.read_text())
    assert len(img_entries) >= 1, 'images/images.yaml has no entries'

    # Step 10: copy artifact, inject minecraft version, push pack file
    artifact_src = _INTEGRATION_DIR / 'puppypack' / 'puppypack-1.0.0.zip'
    shutil.copy(artifact_src, project_dir / artifact_src.name)
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['minecraft'] = '1.21.4'
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'modrinth', '--pack', '--version', '1.0.0')

    versions = mr_api(f'/project/{project_id}/version')
    assert any(v.get('version_number') == '1.0.0' for v in versions), \
        f'version 1.0.0 not found on Modrinth: {[v.get("version_number") for v in versions]}'


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

    # Step 7: modify description + summary, push with images
    desc_file = project_dir / 'description.md'
    desc_file.write_text(desc_file.read_text() + f'\n{_NEW_SENTENCE}\n\n{{{{ img(\'img1\') }}}}\n')
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['summary'] = _UPDATED_SUMMARY
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'modrinth', '--images')

    # Step 8: validate updated page via authenticated API
    mr_data = mr_api(f'/project/{project_id}')
    assert _NEW_SENTENCE in (mr_data.get('body') or ''), 'new sentence not in body after push'
    assert mr_data.get('icon_url'), 'icon_url missing after push'
    gallery = mr_data.get('gallery') or []
    assert len(gallery) >= 1, 'gallery empty after push with images'

    # Step 9: pull with images — summary and images.yaml updated
    run_cli(project_dir, 'pull', '--site', 'modrinth', '--images')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('summary') == _UPDATED_SUMMARY, f'summary not updated after pull: {config.get("summary")!r}'
    images_yaml = project_dir / 'images' / 'images.yaml'
    assert images_yaml.exists(), 'images/images.yaml missing after pull --images'
    img_entries = yaml.safe_load(images_yaml.read_text())
    assert len(img_entries) >= 1, 'images/images.yaml has no entries'

    # Step 10: copy artifact, inject minecraft version, push pack file
    artifact_src = _INTEGRATION_DIR / 'puppymod' / 'puppymod-1.0.0.jar'
    shutil.copy(artifact_src, project_dir / artifact_src.name)
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['minecraft'] = '1.21.4'
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'modrinth', '--pack', '--version', '1.0.0')

    versions = mr_api(f'/project/{project_id}/version')
    assert any(v.get('version_number') == '1.0.0' for v in versions), \
        f'version 1.0.0 not found on Modrinth: {[v.get("version_number") for v in versions]}'
