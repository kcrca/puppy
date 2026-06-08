import yaml
import pytest

pytestmark = pytest.mark.integration


def test_pack_lifecycle(cf_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('pack', {'curseforge': cf_auth['curseforge']})
    slug = inject_slug(project_dir, 'pack')

    run_cli(project_dir, 'create', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('curseforge', {}).get('id'), 'curseforge.id not set after create'


def test_world_lifecycle(cf_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('world', {'curseforge': cf_auth['curseforge']})
    slug = inject_slug(project_dir, 'world')

    run_cli(project_dir, 'create', '--site', 'cf')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config.get('curseforge', {}).get('id'), 'curseforge.id not set after create'
