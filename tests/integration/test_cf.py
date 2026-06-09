import json
import time
import urllib.error
import urllib.parse
import urllib.request
import yaml
import pytest

pytestmark = pytest.mark.integration

from conftest import LifecycleBase, _NEW_SENTENCE, _CF_DASH, _CF_API, _CF_UA


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


def _cf_v1_get(path, token):
    req = urllib.request.Request(
        f'{_CF_API}{path}',
        headers={'X-Api-Token': token, 'User-Agent': _CF_UA},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError:
        return {}


class TestCFPackLifecycle(LifecycleBase):
    SITE = 'cf'
    SITE_KEY = 'curseforge'
    PROJECT_TYPE = 'pack'

    def _cookie(self, ctx):
        return ctx['auth']['curseforge']['cookie']

    def _token(self, ctx):
        return ctx['auth']['curseforge']['token']

    def _assert_create(self, ctx, config):
        cf = _cf_get(f'/projects/{ctx["project_id"]}', self._cookie(ctx))
        assert cf.get('name', '').startswith('Puppy Test Pack'), f'name mismatch: {cf.get("name")!r}'
        assert cf.get('summary') == 'A minimal resource pack for puppy integration testing.'
        assert cf.get('primaryCategoryId') == 393

    def _assert_pull(self, ctx, config):
        assert config['curseforge'].get('id'), 'curseforge.id missing after pull'
        assert config['curseforge'].get('slug'), 'curseforge.slug missing after pull'

    def _before_push_images(self, ctx):
        # Remove pulled description.html so description.md takes priority
        (ctx['project_dir'] / 'curseforge' / 'description.html').unlink(missing_ok=True)

    def _assert_push_images(self, ctx):
        time.sleep(3)  # CF API caches for a few seconds after update
        cf = _cf_get(f'/projects/{ctx["project_id"]}', self._cookie(ctx))
        assert cf.get('summary') == ctx['updated_summary'], f'summary not updated: {cf.get("summary")!r}'
        # Body check via public API — conditional: projects not yet approved return no data
        desc_data = _cf_v1_get(f'/mods/{ctx["project_id"]}/description', self._token(ctx))
        if desc_data.get('data'):
            assert _NEW_SENTENCE in desc_data['data'], 'new sentence not in CF description after push'

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
