import json
import shutil
import time
import urllib.parse
import yaml
import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

_INTEGRATION_DIR = Path(__file__).parent
_UPDATED_SUMMARY = 'Updated summary for CF integration testing.'
_NEW_SENTENCE = 'Updated by integration test.'


def test_pack_lifecycle(cf_auth, make_home, inject_slug, run_cli, cf_api, cf_v1_api):
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

    # Step 7: modify description + summary, push with images
    # Remove pulled description.html so updated description.md takes priority
    cf_desc_html = project_dir / 'curseforge' / 'description.html'
    cf_desc_html.unlink(missing_ok=True)
    desc_file = project_dir / 'description.md'
    desc_file.write_text(desc_file.read_text() + f'\n{_NEW_SENTENCE}\n\n{{{{ img(\'img1\') }}}}\n')
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['summary'] = _UPDATED_SUMMARY
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'cf', '--images')

    # Step 8: validate updated page via authors API + public description API
    # CF API may cache for a few seconds after update
    time.sleep(3)
    cf_data = cf_api(f'/projects/{project_id}')
    assert cf_data.get('summary') == _UPDATED_SUMMARY, f'summary not updated: {cf_data.get("summary")!r}'
    desc_data = cf_v1_api(f'/mods/{project_id}/description')
    # Public description API may return {} for projects not yet approved/published
    if desc_data.get('data'):
        assert _NEW_SENTENCE in desc_data['data'], 'new sentence not in CF description after push'

    # Step 9: pull with images — summary updated; images.yaml written if gallery was available
    run_cli(project_dir, 'pull', '--site', 'cf', '--images')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('summary') == _UPDATED_SUMMARY, f'summary not updated after pull: {config.get("summary")!r}'
    images_yaml = project_dir / 'images' / 'images.yaml'
    if images_yaml.exists():
        img_entries = yaml.safe_load(images_yaml.read_text())
        assert len(img_entries) >= 1, 'images/images.yaml has no entries'

    # Step 10: copy artifact, inject minecraft version, push pack file
    artifact_src = _INTEGRATION_DIR / 'puppypack' / 'puppypack-1.0.0.zip'
    shutil.copy(artifact_src, project_dir / artifact_src.name)
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['minecraft'] = '1.21.4'
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'cf', '--pack', '--version', '1.0.0')

    params = urllib.parse.urlencode({
        'filter': json.dumps({'projectId': project_id}),
        'range': '[0,0]',
        'sort': '["DateCreated","DESC"]',
    })
    files = cf_api(f'/project-files?{params}')
    assert isinstance(files, list) and len(files) >= 1, 'no files found on CF after pack upload'
    assert 'v1.0.0' in (files[0].get('displayName') or ''), \
        f'version 1.0.0 not found in CF file displayName: {files[0].get("displayName")!r}'


def test_world_lifecycle(cf_auth, make_home, inject_slug, run_cli, cf_api, cf_v1_api):
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

    # Step 7: modify description + summary, push with images
    # Remove pulled description.html so updated description.md takes priority
    cf_desc_html = project_dir / 'curseforge' / 'description.html'
    cf_desc_html.unlink(missing_ok=True)
    desc_file = project_dir / 'description.md'
    desc_file.write_text(desc_file.read_text() + f'\n{_NEW_SENTENCE}\n\n{{{{ img(\'img1\') }}}}\n')
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['summary'] = _UPDATED_SUMMARY
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'cf', '--images')

    # Step 8: validate updated page via authors API + public description API
    # CF API may cache for a few seconds after update
    time.sleep(3)
    cf_data = cf_api(f'/projects/{project_id}')
    assert cf_data.get('summary') == _UPDATED_SUMMARY, f'summary not updated: {cf_data.get("summary")!r}'
    desc_data = cf_v1_api(f'/mods/{project_id}/description')
    # Public description API may return {} for projects not yet approved/published
    if desc_data.get('data'):
        assert _NEW_SENTENCE in desc_data['data'], 'new sentence not in CF description after push'

    # Step 9: pull with images — summary updated; images.yaml written if gallery was available
    run_cli(project_dir, 'pull', '--site', 'cf', '--images')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('summary') == _UPDATED_SUMMARY, f'summary not updated after pull: {config.get("summary")!r}'
    images_yaml = project_dir / 'images' / 'images.yaml'
    if images_yaml.exists():
        img_entries = yaml.safe_load(images_yaml.read_text())
        assert len(img_entries) >= 1, 'images/images.yaml has no entries'

    # Step 10: copy artifact, inject minecraft version, push pack file
    artifact_src = _INTEGRATION_DIR / 'puppyworld' / 'puppyworld-1.0.0.zip'
    shutil.copy(artifact_src, project_dir / artifact_src.name)
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['minecraft'] = '1.21.4'
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'cf', '--pack', '--version', '1.0.0')

    params = urllib.parse.urlencode({
        'filter': json.dumps({'projectId': project_id}),
        'range': '[0,0]',
        'sort': '["DateCreated","DESC"]',
    })
    files = cf_api(f'/project-files?{params}')
    assert isinstance(files, list) and len(files) >= 1, 'no files found on CF after pack upload'
    assert 'v1.0.0' in (files[0].get('displayName') or ''), \
        f'version 1.0.0 not found in CF file displayName: {files[0].get("displayName")!r}'
