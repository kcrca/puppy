import urllib.request
import json
import yaml
import pytest

pytestmark = pytest.mark.integration

from conftest import LifecycleBase, _NEW_SENTENCE, _MR_API, _MR_UA, _TEST_SLUG_RE


def _mr_get(path, token):
    req = urllib.request.Request(
        f'{_MR_API}{path}',
        headers={'Authorization': token, 'User-Agent': _MR_UA},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def test_mr_account_empty(mr_auth):
    token = mr_auth['modrinth']['token']
    me = _mr_get('/user/me', token)
    projects = _mr_get(f'/user/{me["username"]}/projects', token)
    stale = [p for p in projects if _TEST_SLUG_RE.match(p.get('slug', ''))]
    assert not stale, f'MR cleanup incomplete — {len(stale)} project(s) still present: {[p["slug"] for p in stale]}'


class TestMRPackLifecycle(LifecycleBase):
    SITE = 'modrinth'
    SITE_KEY = 'modrinth'
    PROJECT_TYPE = 'pack'

    def _token(self, ctx):
        return ctx['auth']['modrinth']['token']

    def _assert_create(self, ctx, config):
        mr = _mr_get(f'/project/{ctx["project_id"]}', self._token(ctx))
        assert mr['title'] == config['name'], f'title mismatch: {mr["title"]!r}'
        assert mr['description'] == 'A minimal resource pack for puppy integration testing.'
        assert set(mr.get('categories', [])) >= {'blocks', 'environment', 'simplistic'}
        assert '16x' in (mr.get('additional_categories') or [])
        assert (mr.get('license') or {}).get('id') == 'MIT', f'license not MIT: {mr.get("license")!r}'
        assert mr.get('source_url') == 'https://github.com/example/puppy-integration-test'
        assert mr.get('discord_url') == 'https://discord.gg/puppytest'

    def _assert_pull(self, ctx, config):
        assert config['modrinth'].get('slug') == ctx['slug']

    def _assert_push_images(self, ctx):
        mr = _mr_get(f'/project/{ctx["project_id"]}', self._token(ctx))
        assert _NEW_SENTENCE in (mr.get('body') or ''), 'new sentence not in body after push'
        assert mr.get('description') == ctx['updated_summary'], \
            f'summary/description mismatch: {mr.get("description")!r}'
        assert mr.get('source_url') == 'https://github.com/example/puppy-integration-test', \
            f'source_url mismatch: {mr.get("source_url")!r}'
        assert mr.get('issues_url') == 'https://github.com/example/puppy-integration-test/issues', \
            f'issues_url mismatch: {mr.get("issues_url")!r}'
        assert mr.get('wiki_url') == 'https://github.com/example/puppy-integration-test/wiki', \
            f'wiki_url mismatch: {mr.get("wiki_url")!r}'
        assert (mr.get('license') or {}).get('id') == 'MIT', \
            f'license not MIT after push: {mr.get("license")!r}'
        assert mr.get('icon_url'), 'icon_url missing after push'
        assert len(mr.get('gallery') or []) >= 1, 'gallery empty after push with images'
        assert any(d.get('id') == 'ko-fi' for d in (mr.get('donation_urls') or [])), \
            f'kofi donation_url missing: {mr.get("donation_urls")!r}'
        assert mr.get('discord_url') == 'https://discord.gg/puppytest', \
            f'discord_url mismatch: {mr.get("discord_url")!r}'

    def _assert_pull_images(self, ctx, config):
        assert config.get('summary') == ctx['updated_summary'], \
            f'summary not updated after pull: {config.get("summary")!r}'
        assert config.get('license') == 'MIT', \
            f'license not pulled back: {config.get("license")!r}'
        assert (config.get('links') or {}).get('source') == 'https://github.com/example/puppy-integration-test', \
            f'links.source not pulled back: {(config.get("links") or {}).get("source")!r}'
        assert (config.get('links') or {}).get('issues') == 'https://github.com/example/puppy-integration-test/issues', \
            f'links.issues not pulled back: {(config.get("links") or {}).get("issues")!r}'
        assert (config.get('links') or {}).get('wiki') == 'https://github.com/example/puppy-integration-test/wiki', \
            f'links.wiki not pulled back: {(config.get("links") or {}).get("wiki")!r}'
        assert (config.get('socials') or {}).get('discord') == 'https://discord.gg/puppytest', \
            f'socials.discord not pulled back: {(config.get("socials") or {}).get("discord")!r}'
        images_yaml = ctx['project_dir'] / 'images' / 'images.yaml'
        assert images_yaml.exists(), 'images/images.yaml missing after pull --images'
        assert len(yaml.safe_load(images_yaml.read_text())) >= 1, 'images/images.yaml has no entries'

    def _assert_push_pack(self, ctx):
        versions = _mr_get(f'/project/{ctx["project_id"]}/version', self._token(ctx))
        v100 = next((v for v in versions if v.get('version_number') == '1.0.0'), None)
        assert v100, f'version 1.0.0 not found on Modrinth: {[v.get("version_number") for v in versions]}'
        assert v100.get('changelog') == 'Initial release for integration testing.', \
            f'changelog mismatch: {v100.get("changelog")!r}'


class TestMRModLifecycle(LifecycleBase):
    SITE = 'modrinth'
    SITE_KEY = 'modrinth'
    PROJECT_TYPE = 'mod'

    def _token(self, ctx):
        return ctx['auth']['modrinth']['token']

    def _assert_create(self, ctx, config):
        mr = _mr_get(f'/project/{ctx["project_id"]}', self._token(ctx))
        assert mr['title'] == config['name'], f'title mismatch: {mr["title"]!r}'
        assert mr['description'] == 'A minimal Fabric mod for puppy integration testing.'
        assert set(mr.get('categories', [])) >= {'utility', 'library'}
        assert (mr.get('license') or {}).get('id') == 'MIT', f'license not MIT: {mr.get("license")!r}'
        assert mr.get('source_url') == 'https://github.com/example/puppy-integration-test'
        assert mr.get('discord_url') == 'https://discord.gg/puppytest'

    def _assert_pull(self, ctx, config):
        assert config['modrinth'].get('slug') == ctx['slug']

    def _assert_push_images(self, ctx):
        mr = _mr_get(f'/project/{ctx["project_id"]}', self._token(ctx))
        assert _NEW_SENTENCE in (mr.get('body') or ''), 'new sentence not in body after push'
        assert mr.get('description') == ctx['updated_summary'], \
            f'summary/description mismatch: {mr.get("description")!r}'
        assert mr.get('source_url') == 'https://github.com/example/puppy-integration-test', \
            f'source_url mismatch: {mr.get("source_url")!r}'
        assert mr.get('issues_url') == 'https://github.com/example/puppy-integration-test/issues', \
            f'issues_url mismatch: {mr.get("issues_url")!r}'
        assert mr.get('wiki_url') == 'https://github.com/example/puppy-integration-test/wiki', \
            f'wiki_url mismatch: {mr.get("wiki_url")!r}'
        assert (mr.get('license') or {}).get('id') == 'MIT', \
            f'license not MIT after push: {mr.get("license")!r}'
        assert mr.get('icon_url'), 'icon_url missing after push'
        assert len(mr.get('gallery') or []) >= 1, 'gallery empty after push with images'
        assert any(d.get('id') == 'ko-fi' for d in (mr.get('donation_urls') or [])), \
            f'kofi donation_url missing: {mr.get("donation_urls")!r}'
        assert mr.get('discord_url') == 'https://discord.gg/puppymod', \
            f'per-site discord override not applied: {mr.get("discord_url")!r}'

    def _assert_pull_images(self, ctx, config):
        assert config.get('summary') == ctx['updated_summary'], \
            f'summary not updated after pull: {config.get("summary")!r}'
        assert config.get('license') == 'MIT', \
            f'license not pulled back: {config.get("license")!r}'
        assert (config.get('links') or {}).get('source') == 'https://github.com/example/puppy-integration-test', \
            f'links.source not pulled back: {(config.get("links") or {}).get("source")!r}'
        assert (config.get('links') or {}).get('issues') == 'https://github.com/example/puppy-integration-test/issues', \
            f'links.issues not pulled back: {(config.get("links") or {}).get("issues")!r}'
        assert (config.get('links') or {}).get('wiki') == 'https://github.com/example/puppy-integration-test/wiki', \
            f'links.wiki not pulled back: {(config.get("links") or {}).get("wiki")!r}'
        assert (config.get('socials') or {}).get('discord') == 'https://discord.gg/puppymod', \
            f'socials.discord not pulled back (mod uses per-site override): {(config.get("socials") or {}).get("discord")!r}'
        images_yaml = ctx['project_dir'] / 'images' / 'images.yaml'
        assert images_yaml.exists(), 'images/images.yaml missing after pull --images'
        assert len(yaml.safe_load(images_yaml.read_text())) >= 1, 'images/images.yaml has no entries'

    def _assert_push_pack(self, ctx):
        versions = _mr_get(f'/project/{ctx["project_id"]}/version', self._token(ctx))
        v100 = next((v for v in versions if v.get('version_number') == '1.0.0'), None)
        assert v100, f'version 1.0.0 not found on Modrinth: {[v.get("version_number") for v in versions]}'
        assert 'fabric' in (v100.get('loaders') or []), f'fabric not in loaders: {v100.get("loaders")!r}'
        assert v100.get('changelog') == 'Initial release for integration testing.', \
            f'changelog mismatch: {v100.get("changelog")!r}'
