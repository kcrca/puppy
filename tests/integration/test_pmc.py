import shutil
import yaml
import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

_INTEGRATION_DIR = Path(__file__).parent
_NEW_SENTENCE = 'Updated by integration test.'


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

    # Step 7: modify description, push with images
    desc_file = project_dir / 'description.md'
    desc_file.write_text(desc_file.read_text() + f'\n{_NEW_SENTENCE}\n\n{{{{ img(\'img1\') }}}}\n')
    run_cli(project_dir, 'push', '--site', 'pmc', '--images')

    # Step 8: validate management page still shows project name
    html = pmc_page(f'https://www.planetminecraft.com/account/manage/texture-packs/{project_id}/')
    assert 'Puppy Test Pack' in html, 'project name not found in PMC management page after push'

    # Step 9: pull with images — images.yaml written
    run_cli(project_dir, 'pull', '--site', 'pmc', '--images')

    images_yaml = project_dir / 'images' / 'images.yaml'
    assert images_yaml.exists(), 'images/images.yaml missing after pull --images'
    img_entries = yaml.safe_load(images_yaml.read_text())
    assert len(img_entries) >= 1, 'images/images.yaml has no entries'

    # Step 10: copy artifact, inject minecraft version, push pack file (PMC records version log)
    artifact_src = _INTEGRATION_DIR / 'puppypack' / 'puppypack-1.0.0.zip'
    shutil.copy(artifact_src, project_dir / artifact_src.name)
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['minecraft'] = '1.21.4'
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'pmc', '--pack', '--version', '1.0.0')

    state = yaml.safe_load((project_dir / '.publish_state.yaml').read_text())
    assert state.get('planetminecraft', {}).get('version') == '1.0.0', \
        f'PMC version log not recorded: {state!r}'


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

    # Step 7: modify description, push with images
    desc_file = project_dir / 'description.md'
    desc_file.write_text(desc_file.read_text() + f'\n{_NEW_SENTENCE}\n\n{{{{ img(\'img1\') }}}}\n')
    run_cli(project_dir, 'push', '--site', 'pmc', '--images')

    # Step 8: validate management page still shows project name
    html = pmc_page(f'https://www.planetminecraft.com/account/manage/projects/{project_id}/')
    assert 'Puppy Test World' in html, 'project name not found in PMC management page after push'

    # Step 9: pull with images — images.yaml written
    run_cli(project_dir, 'pull', '--site', 'pmc', '--images')

    images_yaml = project_dir / 'images' / 'images.yaml'
    assert images_yaml.exists(), 'images/images.yaml missing after pull --images'
    img_entries = yaml.safe_load(images_yaml.read_text())
    assert len(img_entries) >= 1, 'images/images.yaml has no entries'

    # Step 10: copy artifact, inject minecraft version, push pack file (PMC records version log)
    artifact_src = _INTEGRATION_DIR / 'puppyworld' / 'puppyworld-1.0.0.zip'
    shutil.copy(artifact_src, project_dir / artifact_src.name)
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    config['minecraft'] = '1.21.4'
    (project_dir / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
    run_cli(project_dir, 'push', '--site', 'pmc', '--pack', '--version', '1.0.0')

    state = yaml.safe_load((project_dir / '.publish_state.yaml').read_text())
    assert state.get('planetminecraft', {}).get('version') == '1.0.0', \
        f'PMC version log not recorded: {state!r}'
