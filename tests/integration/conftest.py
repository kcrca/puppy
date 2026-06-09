import json
import re
import shutil
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest
import yaml

import puppy.__main__


# Override the unit-test no-op fixtures so integration tests hit real site code.
@pytest.fixture(autouse=True)
def _no_cf_push():
    pass

@pytest.fixture(autouse=True)
def _no_mr_push():
    pass

@pytest.fixture(autouse=True)
def _no_pmc_push():
    pass

@pytest.fixture(autouse=True)
def _no_cf_pull():
    pass

@pytest.fixture(autouse=True)
def _no_mr_pull():
    pass

@pytest.fixture(autouse=True)
def _no_pmc_pull():
    pass

@pytest.fixture(autouse=True)
def _no_mr_upload():
    pass

@pytest.fixture(autouse=True)
def _no_cf_upload():
    pass

@pytest.fixture(autouse=True)
def _no_pmc_upload():
    pass

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

_CF_DASH = 'https://authors.curseforge.com/_api'
_CF_API = 'https://api.curseforge.com/v1'
_CF_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

_TEST_SLUG_RE = re.compile(r'^puppy(?:pack|mod|world)-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$')
_CF_TEST_SLUG_RE = re.compile(r'^puppy-test-(?:pack|mod|world)-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$')


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


def _cf_fetch(url: str, cookie: str) -> dict:
    req = urllib.request.Request(url, headers={
        'User-Agent': _CF_UA,
        'Cookie': cookie,
        'Origin': 'https://authors.curseforge.com',
        'Referer': 'https://authors.curseforge.com/',
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _cf_v1_fetch(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f'{_CF_API}{path}',
        headers={'X-Api-Token': token, 'User-Agent': _CF_UA},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError:
        return {}


def _mr_cleanup(token: str) -> None:
    username = _mr_request('/user/me', token)['username']
    projects = _mr_request(f'/user/{username}/projects', token)
    to_delete = [p for p in projects if _TEST_SLUG_RE.match(p.get('slug', ''))]
    for p in to_delete:
        print(f'\n[cleanup] Deleting Modrinth: {p["slug"]}')
        _mr_request(f'/project/{p["id"]}', token, method='DELETE')


def _cf_delete_project(project_id: int, cookie: str) -> None:
    req = urllib.request.Request(
        f'{_CF_DASH}/projects/{project_id}',
        method='DELETE',
        headers={
            'User-Agent': _CF_UA,
            'Cookie': cookie,
            'Origin': 'https://authors.curseforge.com',
            'Referer': 'https://authors.curseforge.com/',
        },
    )
    with urllib.request.urlopen(req) as _:
        pass


def _cf_cleanup(cookie: str) -> None:
    params = urllib.parse.urlencode({'filter': '{}', 'range': '[0,99]', 'sort': '["id","DESC"]'})
    try:
        data = _cf_fetch(f'{_CF_DASH}/projects?{params}', cookie)
    except Exception:
        return
    if not isinstance(data, list):
        return
    stale = [p for p in data if _TEST_SLUG_RE.match(p.get('slug', '')) or _CF_TEST_SLUG_RE.match(p.get('slug', ''))]
    for p in stale:
        print(f'\n[cleanup] Deleting CurseForge: {p["slug"]}')
        try:
            _cf_delete_project(p['id'], cookie)
        except Exception as e:
            print(f'[cleanup] Warning: failed to delete {p["slug"]}: {e}')


@pytest.fixture(scope='session')
def _auth():
    return _load_auth()


@pytest.fixture(scope='session', autouse=True)
def _cleanup_prior_runs(_auth):
    token = _auth.get('modrinth', {}).get('token')
    if token:
        _mr_cleanup(token)

    cf_cookie = _auth.get('curseforge', {}).get('cookie')
    if cf_cookie:
        _cf_cleanup(cf_cookie)



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


@pytest.fixture(scope='session')
def artifacts(run_id, tmp_path_factory):
    import io
    import zipfile
    base_dir = tmp_path_factory.mktemp('artifacts')
    sources = {
        'puppypack': (_INTEGRATION_DIR / 'puppypack' / 'puppypack-1.0.0.zip', '.zip'),
        'puppymod':  (_INTEGRATION_DIR / 'puppymod'  / 'puppymod-1.0.0.jar',  '.jar'),
        'puppyworld':(_INTEGRATION_DIR / 'puppyworld' / 'puppyworld-1.0.0.zip', '.zip'),
    }
    result = {}
    for name, (src, ext) in sources.items():
        dest = base_dir / f'{name}-1.0.0{ext}'
        buf = io.BytesIO(src.read_bytes())
        with zipfile.ZipFile(buf, 'a') as zf:
            zf.writestr('puppy-run-id.txt', run_id)
        dest.write_bytes(buf.getvalue())
        result[name] = dest
    return result


@pytest.fixture
def make_home(tmp_path):
    def _make(project_type: str, auth: dict) -> tuple[Path, Path]:
        project_name = _PROJECT_NAME[project_type]
        home = tmp_path / 'puppy'
        home.mkdir()

        shutil.copytree(_PUPPY_HOME / project_name, home / project_name)
        home_config = yaml.safe_load((_PUPPY_HOME / 'puppy.yaml').read_text()) or {}
        home_config['projects'] = [project_name]
        (home / 'puppy.yaml').write_text(yaml.dump(home_config, default_flow_style=False))
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
        if config.get('name'):
            config['name'] = f'{config["name"]} {run_id}'
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


@pytest.fixture
def mr_api(_auth):
    token = _auth.get('modrinth', {}).get('token', '')
    return lambda path: _mr_request(path, token)


@pytest.fixture
def cf_api(_auth):
    cookie = _auth.get('curseforge', {}).get('cookie', '')
    return lambda path: _cf_fetch(f'{_CF_DASH}{path}', cookie)


@pytest.fixture
def cf_v1_api(_auth):
    token = _auth.get('curseforge', {}).get('token', '')
    return lambda path: _cf_v1_fetch(path, token)


@pytest.fixture
def pmc_page(_auth):
    cookie_str = _auth.get('planetminecraft', {}).get('cookie', '')
    name, _, value = cookie_str.partition('=')

    def _fetch(url: str) -> str:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            ctx = browser.new_context()
            if name and value:
                ctx.add_cookies([{
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': 'www.planetminecraft.com',
                    'path': '/',
                }])
            page = ctx.new_page()
            page.goto(url, wait_until='networkidle')
            html = page.content()
            browser.close()
            return html
    return _fetch
