import urllib.request

import pytest
import yaml

pytestmark = pytest.mark.integration

_MR_API = 'https://api.modrinth.com/v2'
_MR_UA = 'puppy/1.0'


def _mr_delete(project_id: str, auth: dict) -> None:
    req = urllib.request.Request(
        f'{_MR_API}/project/{project_id}',
        method='DELETE',
        headers={'Authorization': auth['modrinth']['token'], 'User-Agent': _MR_UA},
    )
    urllib.request.urlopen(req)


def _mr_id(project_dir) -> str | None:
    config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    return config.get('modrinth', {}).get('id')


def test_pack_lifecycle(mr_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('pack', {'modrinth': mr_auth['modrinth']})
    slug = inject_slug(project_dir, 'pack')

    try:
        run_cli(project_dir, 'create', '--site', 'modrinth')
        run_cli(project_dir, 'pull', '--site', 'modrinth')

        config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
        assert config['modrinth']['slug'] == slug
        assert config['name'] == 'Puppy Integration Test Pack'
        assert config.get('license') == 'MIT'
        assert config['modrinth'].get('resolution') == ['16x']

    finally:
        project_id = _mr_id(project_dir)
        if project_id:
            _mr_delete(project_id, mr_auth)


def test_mod_lifecycle(mr_auth, make_home, inject_slug, run_cli):
    home, project_dir = make_home('mod', {'modrinth': mr_auth['modrinth']})
    slug = inject_slug(project_dir, 'mod')

    try:
        run_cli(project_dir, 'create', '--site', 'modrinth')
        run_cli(project_dir, 'pull', '--site', 'modrinth')

        config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
        assert config['modrinth']['slug'] == slug
        assert config['name'] == 'Puppy Integration Test Mod'
        assert config.get('license') == 'MIT'

    finally:
        project_id = _mr_id(project_dir)
        if project_id:
            _mr_delete(project_id, mr_auth)
