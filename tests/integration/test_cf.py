import json
import time
import urllib.parse
import urllib.request
import yaml
import pytest

pytestmark = pytest.mark.integration

from conftest import LifecycleBase, _CF_DASH, _CF_UA, _TEST_SLUG_RE, _CF_TEST_SLUG_RE


def _cf_get(path, cookie):
    req = urllib.request.Request(
        f'{_CF_DASH}{path}',
        headers={
            'User-Agent': _CF_UA,
            'Cookie': cookie,
            'Origin': 'https://authors.curseforge.com',
            'Referer': 'https://authors.curseforge.com/',
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def test_cf_account_empty(cf_auth):
    cookie = cf_auth['curseforge']['cookie']
    params = urllib.parse.urlencode({'filter': '{}', 'range': '[0,99]', 'sort': '["id","DESC"]'})
    try:
        data = _cf_get(f'/projects?{params}', cookie)
    except Exception:
        data = []
    if not isinstance(data, list):
        data = []
    stale = [
        p for p in data
        if _TEST_SLUG_RE.match(p.get('slug', '')) or _CF_TEST_SLUG_RE.match(p.get('slug', ''))
    ]
    assert not stale, f'CF cleanup incomplete — {len(stale)} project(s) still present: {[p["slug"] for p in stale]}'


class TestCFPackLifecycle(LifecycleBase):
    SITE = 'cf'
    SITE_KEY = 'curseforge'
    PROJECT_TYPE = 'pack'

    def _cookie(self, ctx):
        return ctx['auth']['curseforge']['cookie']

    def _assert_create(self, ctx, config):
        cf = _cf_get(f'/projects/{ctx["project_id"]}', self._cookie(ctx))
        assert cf.get('name', '').startswith('Puppy Test Pack'), f'name mismatch: {cf.get("name")!r}'
        assert cf.get('summary') == 'A minimal resource pack for puppy integration testing.'
        assert cf.get('primaryCategoryId') == 393

    def _assert_pull(self, ctx, config):
        assert config['curseforge'].get('id'), 'curseforge.id missing after pull'
        assert config['curseforge'].get('slug'), 'curseforge.slug missing after pull'

    def _assert_push_images(self, ctx):
        time.sleep(3)  # CF API caches for a few seconds after update
        cf = _cf_get(f'/projects/{ctx["project_id"]}', self._cookie(ctx))
        assert cf.get('summary') == ctx['updated_summary'], f'summary not updated: {cf.get("summary")!r}'

    def _assert_pull_images(self, ctx, config):
        assert config.get('summary') == ctx['updated_summary'], \
            f'summary not updated after pull: {config.get("summary")!r}'
        images_yaml = ctx['project_dir'] / 'images' / 'images.yaml'
        if images_yaml.exists():
            assert len(yaml.safe_load(images_yaml.read_text())) >= 1, 'images/images.yaml has no entries'

    def _assert_push_pack(self, ctx):
        params = urllib.parse.urlencode({
            'filter': json.dumps({'projectId': ctx['project_id']}),
            'range': '[0,0]',
            'sort': '["DateCreated","DESC"]',
        })
        files = _cf_get(f'/project-files?{params}', self._cookie(ctx))
        assert isinstance(files, list) and len(files) >= 1, 'no files found on CF after pack upload'
        assert 'v1.0.0' in (files[0].get('displayName') or ''), \
            f'version 1.0.0 not found in CF file displayName: {files[0].get("displayName")!r}'


class TestCFWorldLifecycle(TestCFPackLifecycle):
    PROJECT_TYPE = 'world'

    def _assert_create(self, ctx, config):
        cf = _cf_get(f'/projects/{ctx["project_id"]}', self._cookie(ctx))
        assert cf.get('name', '').startswith('Puppy Test World'), f'name mismatch: {cf.get("name")!r}'
        assert cf.get('summary') == 'A minimal world save for puppy integration testing.'
        assert cf.get('primaryCategoryId') == 253


class TestCFBedrockPackLifecycle(TestCFPackLifecycle):
    PROJECT_TYPE = 'pack'

    def _extra_config(self):
        return {'bedrock': True}

    def _assert_create(self, ctx, config):
        assert config.get('curseforge', {}).get('bedrock') is True, \
            'curseforge.bedrock not set after create'
        cf = _cf_get(f'/projects/{ctx["project_id"]}', self._cookie(ctx))
        assert cf.get('classId') == 4559, f'expected classId 4559 (Addons), got {cf.get("classId")}'
        assert cf.get('primaryCategoryId') == 4561, \
            f'expected primaryCategoryId 4561 (Resource Packs), got {cf.get("primaryCategoryId")}'

    def _assert_pull(self, ctx, config):
        super()._assert_pull(ctx, config)
        assert config.get('curseforge', {}).get('bedrock') is True, \
            'curseforge.bedrock missing after pull'


class TestCFBedrockWorldLifecycle(TestCFWorldLifecycle):
    PROJECT_TYPE = 'world'

    def _extra_config(self):
        return {'bedrock': True}

    def _assert_create(self, ctx, config):
        assert config.get('curseforge', {}).get('bedrock') is True, \
            'curseforge.bedrock not set after create'
        cf = _cf_get(f'/projects/{ctx["project_id"]}', self._cookie(ctx))
        assert cf.get('classId') == 4559, f'expected classId 4559 (Addons), got {cf.get("classId")}'
        assert cf.get('primaryCategoryId') == 4560, \
            f'expected primaryCategoryId 4560 (Worlds), got {cf.get("primaryCategoryId")}'

    def _assert_pull(self, ctx, config):
        super()._assert_pull(ctx, config)
        assert config.get('curseforge', {}).get('bedrock') is True, \
            'curseforge.bedrock missing after pull'
