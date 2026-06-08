import json
import re
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest
import yaml

import puppy.__main__

_INTEGRATION_DIR = Path(__file__).parent
_PUPPY_HOME = _INTEGRATION_DIR / 'puppy'
_AUTH_FILE = _PUPPY_HOME / 'auth.yaml'

_PROJECT_NAME = {
    'pack': 'puppypack',
    'mod': 'puppymod',
    'world': 'puppyworld',
}

_MR_API = 'https://api.modrinth.com/v2'
_MR_UA = 'puppy-test/1.0'

_TEST_SLUG_RE = re.compile(r'^puppy(?:pack|mod|world)-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$')


def _load_auth() -> dict:
    if not _AUTH_FILE.exists():
        return {}
    return yaml.safe_load(_AUTH_FILE.read_text()) or {}


def _mr_request(path: str, token: str, method: str = 'GET') -> object:
    req = urllib.request.Request(
        f'{_MR_API}{path}',
        method=method,
        headers={'Authorization': token, 'User-Agent': _MR_UA},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()) if method == 'GET' else None


def _mr_cleanup(token: str) -> None:
    username = _mr_request('/user', token)['username']
    projects = _mr_request(f'/user/{username}/projects', token)
    to_delete = [p for p in projects if _TEST_SLUG_RE.match(p.get('slug', ''))]
    for p in to_delete:
        print(f'\n[cleanup] Deleting Modrinth: {p["slug"]}')
        _mr_request(f'/project/{p["id"]}', token, method='DELETE')


@pytest.fixture(scope='session')
def _auth():
    return _load_auth()


@pytest.fixture(scope='session', autouse=True)
def _cleanup_prior_runs(_auth):
    token = _auth.get('modrinth', {}).get('token')
    if token:
        _mr_cleanup(token)
    # CurseForge and PMC have no delete API — remove old test projects manually.


@pytest.fixture
def mr_auth(_auth):
    if not _auth.get('modrinth', {}).get('token'):
        pytest.skip('no Modrinth credentials — add to tests/integration/puppy/auth.yaml')
    return _auth


@pytest.fixture
def cf_auth(_auth):
    cf = _auth.get('curseforge', {})
    if not cf.get('token') or not cf.get('cookie'):
        pytest.skip('no CurseForge credentials — add to tests/integration/puppy/auth.yaml')
    return _auth


@pytest.fixture
def pmc_auth(_auth):
    if not _auth.get('planetminecraft'):
        pytest.skip('no PMC credentials — add to tests/integration/puppy/auth.yaml')
    return _auth


@pytest.fixture(scope='session')
def run_id():
    return datetime.now().strftime('%y-%m-%d-%H-%M')


@pytest.fixture
def make_home(tmp_path):
    def _make(project_type: str, auth: dict) -> tuple[Path, Path]:
        project_name = _PROJECT_NAME[project_type]
        home = tmp_path / 'puppy'
        home.mkdir()

        shutil.copytree(_PUPPY_HOME / project_name, home / project_name)
        (home / 'puppy.yaml').write_text(yaml.dump({'projects': [project_name]}))
        shutil.copy(_PUPPY_HOME / '.gitignore', home / '.gitignore')
        (home / 'auth.yaml').write_text(yaml.dump(auth))

        return home, home / project_name

    return _make


@pytest.fixture
def inject_slug(run_id):
    def _inject(project_dir: Path, project_type: str) -> str:
        slug = f'{_PROJECT_NAME[project_type]}-{run_id}'
        config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
        config['pack'] = slug
        (project_dir / 'puppy.yaml').write_text(yaml.dump(config))
        return slug
    return _inject


@pytest.fixture
def run_cli(monkeypatch):
    def _run(project_dir: Path, *args: str) -> None:
        monkeypatch.chdir(project_dir)
        monkeypatch.setattr('sys.argv', ['puppy', '--no-open'] + list(args))
        try:
            puppy.__main__.main()
        except SystemExit as e:
            if e.code and e.code != 0:
                raise AssertionError(f'puppy {list(args)!r} failed with exit code {e.code}')
    return _run
