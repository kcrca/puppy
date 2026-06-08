import pytest
import yaml

pytestmark = pytest.mark.integration

# CurseForge has no public project delete API.
# Test projects created here must be removed manually at curseforge.com/my-projects.


def _cf_id(project_dir) -> int | None:
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    return config.get('curseforge', {}).get('id')


def test_pack_lifecycle(cf_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('pack', {'curseforge': cf_auth['curseforge']})
    slug = inject_slug(project_dir, 'pack')

    run_cli(project_dir, 'create', '--site', 'cf')
    run_cli(project_dir, 'pull', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['name'] == 'Puppy Integration Test Pack'
    assert config['curseforge'].get('id') is not None

    project_id = _cf_id(project_dir)
    pytest.skip(f'CF project {project_id} created — delete manually at curseforge.com/my-projects')


def test_world_lifecycle(cf_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('world', {'curseforge': cf_auth['curseforge']})
    slug = inject_slug(project_dir, 'world')

    run_cli(project_dir, 'create', '--site', 'cf')
    run_cli(project_dir, 'pull', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['name'] == 'Puppy Integration Test World'
    assert config['curseforge'].get('id') is not None

    project_id = _cf_id(project_dir)
    pytest.skip(f'CF project {project_id} created — delete manually at curseforge.com/my-projects')
