import re
import yaml
import pytest
from bs4 import BeautifulSoup

pytestmark = pytest.mark.integration

from conftest import LifecycleBase, _PMC_BASE


def _pmc_fetch(manage_path, ctx, project_id=None):
    from playwright.sync_api import sync_playwright
    if project_id is None:
        project_id = ctx['project_id']
    url = f'{_PMC_BASE}{manage_path}{project_id}/'
    cookie_str = ctx['auth']['planetminecraft']['cookie']
    c_name, _, c_value = cookie_str.partition('=')
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        pctx = browser.new_context()
        pctx.add_cookies([{
            'name': c_name.strip(), 'value': c_value.strip(),
            'domain': 'www.planetminecraft.com', 'path': '/',
        }])
        page = pctx.new_page()
        page.goto(url, wait_until='networkidle')
        html = page.content()
        browser.close()
    return html


def test_pmc_account_empty(pmc_auth, pmc_page):
    remaining = []
    for path in ('/account/manage/texture-packs/', '/account/manage/projects/'):
        soup = BeautifulSoup(pmc_page(f'{_PMC_BASE}{path}'), 'html.parser')
        for a in soup.find_all('a', href=re.compile(rf'{re.escape(path)}\d+/')):
            m = re.search(r'/(\d+)/', a['href'])
            if m:
                remaining.append(int(m.group(1)))
    remaining = list(dict.fromkeys(remaining))
    assert not remaining, f'PMC cleanup incomplete — {len(remaining)} project(s) still present: {remaining}'


class TestPMCPackLifecycle(LifecycleBase):
    SITE = 'pmc'
    SITE_KEY = 'planetminecraft'
    PROJECT_TYPE = 'pack'
    PMC_MANAGE_PATH = '/account/manage/texture-packs/'

    def _assert_create(self, ctx, config):
        html = _pmc_fetch(self.PMC_MANAGE_PATH, ctx)
        assert ctx['project_name'] in html, 'project name not found in PMC management page'

    def _assert_pull(self, ctx, config):
        assert config['planetminecraft'].get('id'), 'planetminecraft.id missing after pull'
        assert config['planetminecraft'].get('slug'), 'planetminecraft.slug missing after pull'

    def _assert_push_images(self, ctx):
        html = _pmc_fetch(self.PMC_MANAGE_PATH, ctx)
        assert ctx['project_name'] in html, 'project name not found in PMC management page after push'

    def _assert_pull_images(self, ctx, config):
        images_yaml = ctx['project_dir'] / 'images' / 'images.yaml'
        assert images_yaml.exists(), 'images/images.yaml missing after pull --images'
        assert len(yaml.safe_load(images_yaml.read_text())) >= 1, 'images/images.yaml has no entries'

    def _assert_push_pack(self, ctx):
        html = _pmc_fetch(self.PMC_MANAGE_PATH, ctx)
        assert 'Update v1.0.0' in html, 'PMC version log entry not found on manage page'


class TestPMCWorldLifecycle(TestPMCPackLifecycle):
    PROJECT_TYPE = 'world'
    PMC_MANAGE_PATH = '/account/manage/projects/'

    def _assert_create(self, ctx, config):
        html = _pmc_fetch(self.PMC_MANAGE_PATH, ctx)
        assert ctx['project_name'] in html, 'project name not found in PMC management page'

    def _assert_push_images(self, ctx):
        html = _pmc_fetch(self.PMC_MANAGE_PATH, ctx)
        assert ctx['project_name'] in html, 'project name not found in PMC management page after push'


class TestPMCBedrockPackLifecycle(TestPMCPackLifecycle):
    PMC_MANAGE_PATH = '/account/manage/texture-packs/'

    def _extra_config(self):
        return {'bedrock': True}

    def _assert_create(self, ctx, config):
        assert config.get('planetminecraft', {}).get('bedrock') is True, \
            'planetminecraft.bedrock not set after create'
        html = _pmc_fetch(self.PMC_MANAGE_PATH, ctx)
        assert ctx['project_name'] in html, 'project name not found in PMC management page'

    def _assert_pull(self, ctx, config):
        super()._assert_pull(ctx, config)
        assert config.get('planetminecraft', {}).get('bedrock') is True, \
            'planetminecraft.bedrock missing after pull'


class TestPMCBedrockWorldLifecycle(TestPMCWorldLifecycle):
    PMC_MANAGE_PATH = '/account/manage/projects/'

    def _extra_config(self):
        return {'bedrock': True}

    def _assert_create(self, ctx, config):
        assert config.get('planetminecraft', {}).get('bedrock') is True, \
            'planetminecraft.bedrock not set after create'
        html = _pmc_fetch(self.PMC_MANAGE_PATH, ctx)
        assert ctx['project_name'] in html, 'project name not found in PMC management page'

    def _assert_pull(self, ctx, config):
        super()._assert_pull(ctx, config)
        assert config.get('planetminecraft', {}).get('bedrock') is True, \
            'planetminecraft.bedrock missing after pull'
