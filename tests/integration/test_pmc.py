import pytest
import yaml

pytestmark = pytest.mark.integration

# PMC delete endpoint not yet investigated.
# Test projects created here must be removed manually at planetminecraft.com.


def _pmc_id(project_dir) -> int | None:
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    return config.get('planetminecraft', {}).get('id')


def test_pack_lifecycle(pmc_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('pack', {'planetminecraft': pmc_auth['planetminecraft']})
    slug = inject_slug(project_dir, 'pack')

    run_cli(project_dir, 'create', '--site', 'pmc')
    run_cli(project_dir, 'pull', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['name'] == 'Puppy Integration Test Pack'
    assert config['planetminecraft'].get('id') is not None
    assert config['planetminecraft'].get('resolution') == 16

    project_id = _pmc_id(project_dir)
    pytest.skip(f'PMC project {project_id} created — delete manually at planetminecraft.com')


def test_world_lifecycle(pmc_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('world', {'planetminecraft': pmc_auth['planetminecraft']})
    slug = inject_slug(project_dir, 'world')

    run_cli(project_dir, 'create', '--site', 'pmc')
    run_cli(project_dir, 'pull', '--site', 'pmc')

    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert config['name'] == 'Puppy Integration Test World'
    assert config['planetminecraft'].get('id') is not None
    assert config['planetminecraft'].get('progress') == 50

    project_id = _pmc_id(project_dir)
    pytest.skip(f'PMC project {project_id} created — delete manually at planetminecraft.com')
