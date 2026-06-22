import os
import re
import shutil
import sys
import urllib.request
import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml

import puppy.__main__
from puppy.errors import AuthExpiredError
from cleanup import (  # noqa: F401  (several are re-exported to test modules)
    _load_auth,
    _mr_request, _cf_fetch, run_cleanup,
    _CF_DASH, _CF_UA, _MR_API, _MR_UA, _PMC_BASE,
)


def pytest_configure(config):
    # Skips here carry a real reason (missing creds, expired auth, CF daily-update
    # limit). Force them to print so you don't have to remember -rs on every run.
    chars = config.option.reportchars or ''
    if 's' not in chars:
        config.option.reportchars = chars + 's'


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

@pytest.fixture(autouse=True)
def _no_images():
    pass

_INTEGRATION_DIR = Path(__file__).parent
_PUPPY_HOME = _INTEGRATION_DIR / 'puppy'
_AUTH_FILE = _PUPPY_HOME / 'auth.yaml'

_PROJECT_NAME = {
    'pack': 'puppypack',
    'mod': 'puppymod',
    'world': 'puppyworld',
}

_PMC_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
_CF_API = 'https://api.curseforge.com/v1'

_TEST_SLUG_RE = re.compile(r'^puppy(?:pack|mod|world)-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$')
_CF_TEST_SLUG_RE = re.compile(r'^puppy-test-(?:pack|mod|world)-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$')


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


@pytest.fixture(scope='session')
def _auth():
    return _load_auth()


@pytest.fixture(scope='session', autouse=True)
def _cleanup_prior_runs(_auth, request):
    worker_id = getattr(request.config, 'workerinput', {}).get('workerid', 'master')
    if worker_id in ('master', 'gw0'):
        run_cleanup(_auth)



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
        config['handle'] = slug
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


# ---------------------------------------------------------------------------
# Shared lifecycle constants
# ---------------------------------------------------------------------------

_NEW_SENTENCE = 'Updated by integration test.'


# ---------------------------------------------------------------------------
# Base class for per-site lifecycle test classes
# ---------------------------------------------------------------------------

class LifecycleBase:
    SITE = ''         # CLI site argument: 'modrinth', 'cf', 'pmc'
    SITE_KEY = ''     # auth.yaml / puppy.yaml key: 'modrinth', 'curseforge', 'planetminecraft'
    PROJECT_TYPE = 'pack'

    @pytest.fixture(scope='class')
    def ctx(self, tmp_path_factory, run_id, artifacts, _auth):
        site_auth = _auth.get(self.SITE_KEY)
        if not site_auth:
            pytest.skip(f'no {self.SITE_KEY} credentials')

        project_name = _PROJECT_NAME[self.PROJECT_TYPE]
        root = tmp_path_factory.mktemp(f'{self.SITE}_{self.PROJECT_TYPE}')
        home = root / 'puppy'
        home.mkdir()
        shutil.copytree(_PUPPY_HOME / project_name, home / project_name)

        home_config = yaml.safe_load((_PUPPY_HOME / 'puppy.yaml').read_text()) or {}
        home_config['projects'] = [project_name]
        (home / 'puppy.yaml').write_text(yaml.dump(home_config, default_flow_style=False))
        shutil.copy(_PUPPY_HOME / '.gitignore', home / '.gitignore')
        (home / 'auth.yaml').write_text(yaml.dump({self.SITE_KEY: site_auth}))

        project_dir = home / project_name
        slug = f'{project_name}-{run_id}'
        config = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
        config['handle'] = slug
        if config.get('name'):
            config['name'] = f'{config["name"]} {run_id}'
        config.update(self._extra_config())
        (project_dir / 'puppy.yaml').write_text(yaml.dump(config))

        return {
            'project_dir': project_dir,
            'slug': slug,
            'project_name': config.get('name', ''),
            'project_id': None,
            'artifacts': artifacts,
            'auth': _auth,
            'updated_summary': f'Updated summary for {self.SITE} {self.PROJECT_TYPE} integration testing.',
        }

    def _run(self, ctx, *args):
        if ctx.get('_auth_error'):
            pytest.skip(ctx['_auth_error'])
        orig_argv = sys.argv[:]
        orig_dir = os.getcwd()
        os.chdir(ctx['project_dir'])
        sys.argv = ['puppy', '--no-open'] + list(args)
        try:
            puppy.__main__.main()
        except AuthExpiredError as e:
            reason = f'{self.SITE_KEY} auth expired (HTTP {e.code}) — check tests/integration/puppy/auth.yaml'
            ctx['_auth_error'] = reason
            pytest.skip(reason)
        except SystemExit as e:
            if e.code and e.code != 0:
                msg = str(e.code)
                if 'auth expired' in msg.lower() or 'daily update limit' in msg.lower():
                    ctx['_auth_error'] = msg
                    pytest.skip(msg)
                raise AssertionError(f'puppy {list(args)!r} failed with exit code {e.code}')
        finally:
            sys.argv = orig_argv
            os.chdir(orig_dir)

    # ------------------------------------------------------------------
    # Test steps
    # ------------------------------------------------------------------

    def test_01_create(self, ctx):
        self._run(ctx, 'create', '--site', self.SITE)
        config = yaml.safe_load((ctx['project_dir'] / 'puppy.yaml').read_text())
        assert config.get(self.SITE_KEY, {}).get('id'), f'{self.SITE_KEY}.id not set after create'
        ctx['project_id'] = config[self.SITE_KEY]['id']
        self._assert_create(ctx, config)

    def test_02_pull(self, ctx):
        self._run(ctx, 'pull', '--site', self.SITE)
        config = yaml.safe_load((ctx['project_dir'] / 'puppy.yaml').read_text())
        assert config.get(self.SITE_KEY, {}).get('id'), f'{self.SITE_KEY}.id missing after pull'
        self._assert_pull(ctx, config)

    def test_03_push_images(self, ctx):
        desc_file = ctx['project_dir'] / 'description.md'
        desc_file.write_text(desc_file.read_text() + f'\n{_NEW_SENTENCE}\n\n{{{{ img(\'img1\') }}}}\n')
        config = yaml.safe_load((ctx['project_dir'] / 'puppy.yaml').read_text())
        config['summary'] = ctx['updated_summary']
        (ctx['project_dir'] / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
        self._before_push_images(ctx)
        self._run(ctx, 'push', '--site', self.SITE, '-c', 'images')
        self._assert_push_images(ctx)

    def test_04_pull_images(self, ctx):
        self._run(ctx, 'pull', '--site', self.SITE, '-c', 'images')
        config = yaml.safe_load((ctx['project_dir'] / 'puppy.yaml').read_text())
        self._assert_pull_images(ctx, config)

    def test_05_push_pack(self, ctx):
        artifact_src = ctx['artifacts'][f'puppy{self.PROJECT_TYPE}']
        shutil.copy(artifact_src, ctx['project_dir'] / artifact_src.name)
        config = yaml.safe_load((ctx['project_dir'] / 'puppy.yaml').read_text())
        config['minecraft'] = '1.21.4'
        config['version'] = '1.0.0'
        (ctx['project_dir'] / 'puppy.yaml').write_text(yaml.dump(config, default_flow_style=False))
        self._run(ctx, 'push', '--site', self.SITE, '-c', 'file')
        self._assert_push_pack(ctx)

    # ------------------------------------------------------------------
    # Override in subclasses
    # ------------------------------------------------------------------

    def _extra_config(self) -> dict: return {}
    def _assert_create(self, ctx, config): pass
    def _assert_pull(self, ctx, config): pass
    def _before_push_images(self, ctx): pass
    def _assert_push_images(self, ctx): pass
    def _assert_pull_images(self, ctx, config): pass
    def _assert_push_pack(self, ctx): pass
