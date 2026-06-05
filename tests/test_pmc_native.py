import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup
from PIL import Image

from puppy.core import Project
from puppy.errors import AuthExpiredError
from puppy.sites import PMC
from puppy.syncer import _run_pmc_native as _run_pmc_native_real


_AUTH = {'planetminecraft': 'pmc_autologin=test-cookie'}
_PROJECT_ID = 999

_CSRF = 'csrf-token-abc'
_EDIT_HTML = '''
<meta id="core-csrf-token" content="csrf-token-abc">
<input name="member_id" value="42">
<input name="subject_id" value="999">
<input name="group" value="texture_packs">
<input name="module" value="texture_pack">
<input name="module_task" value="edit_texture_pack">
<select id="op1"><option value="1.21" selected>1.21</option></select>
'''

_EDIT_SOUP = BeautifulSoup(_EDIT_HTML, 'html.parser')


def _make_response(body: bytes | str | dict | None, status: int = 200):
    if body is None:
        encoded = b''
    elif isinstance(body, dict):
        encoded = json.dumps(body).encode()
    elif isinstance(body, str):
        encoded = body.encode()
    else:
        encoded = body
    resp = MagicMock()
    resp.read.return_value = encoded
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _make_http_error(code: int, body: str = ''):
    return urllib.error.HTTPError(url='', code=code, msg='', hdrs={}, fp=io.BytesIO(body.encode()))


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, 'html.parser')


# ── 1. _pmc_get_page ─────────────────────────────────────────────────────────

def test_pmc_get_page_extracts_csrf():
    from puppy.sites.planetminecraft import _pmc_get_page
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_EDIT_HTML)
        soup, csrf = _pmc_get_page(_PROJECT_ID, 'pmc_autologin=x')
    assert csrf == _CSRF
    assert soup.find('input', {'name': 'member_id'}) is not None


def test_pmc_get_page_raises_auth_expired_when_no_csrf():
    from puppy.sites.planetminecraft import _pmc_get_page
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response('<html>no token here</html>')
        with pytest.raises(AuthExpiredError):
            _pmc_get_page(_PROJECT_ID, 'pmc_autologin=x')


# ── 2. _pmc_post ─────────────────────────────────────────────────────────────

def test_pmc_post_sends_multipart_to_ajax():
    from puppy.sites.planetminecraft import _pmc_post
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response({'status': 'success'})
        result = _pmc_post(_PROJECT_ID, 'pmc_autologin=x', _CSRF, [('foo', 'bar')])

    req = mock_open.call_args[0][0]
    assert 'ajax.php' in req.full_url
    assert req.get_method() == 'POST'
    ct = req.get_header('Content-type')
    assert ct.startswith('multipart/form-data; boundary=')
    assert b'foo' in req.data
    assert b'bar' in req.data
    assert result == {'status': 'success'}


def test_pmc_post_401_raises_auth_expired():
    from puppy.sites.planetminecraft import _pmc_post
    with patch('urllib.request.urlopen', side_effect=_make_http_error(401, 'Unauthorized')):
        with pytest.raises(AuthExpiredError) as exc_info:
            _pmc_post(_PROJECT_ID, 'pmc_autologin=x', _CSRF, [('x', 'y')])
    assert exc_info.value.code == 401


# ── 3. _pmc_sync_gallery ─────────────────────────────────────────────────────

def test_pmc_sync_gallery_uploads_new_images(tmp_path):
    from puppy.sites.planetminecraft import _pmc_sync_gallery
    img_path = tmp_path / 'banner.png'
    Image.new('RGB', (200, 100), color='green').save(img_path)

    image_list = [{'file': 'banner', 'description': 'A nice banner'}]
    responses = [
        _make_response({'media_id': 77}),
        _make_response({'status': 'success'}),
    ]

    with patch('urllib.request.urlopen', side_effect=responses):
        with patch('puppy.sites.planetminecraft.find_image', return_value=img_path):
            with patch('puppy.sites.planetminecraft.prepare_gallery_image', return_value=b'IMGDATA'):
                _pmc_sync_gallery(_PROJECT_ID, 'pmc_autologin=x', _CSRF, _EDIT_SOUP, image_list, tmp_path, 0)


def test_pmc_sync_gallery_skips_existing(tmp_path):
    from puppy.sites.planetminecraft import _pmc_sync_gallery
    soup = _soup(_EDIT_HTML + '<div data-media-item-id="55" data-caption="banner - Cool">')
    image_list = [{'file': 'banner', 'description': 'Cool'}]

    with patch('urllib.request.urlopen') as mock_open:
        _pmc_sync_gallery(_PROJECT_ID, 'pmc_autologin=x', _CSRF, soup, image_list, tmp_path, 0)

    assert mock_open.call_count == 0


def test_pmc_sync_gallery_deletes_removed(tmp_path):
    from puppy.sites.planetminecraft import _pmc_sync_gallery
    soup = _soup(_EDIT_HTML + '<div data-media-item-id="88" data-caption="old-image">')
    image_list = []

    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response({'status': 'success'})
        _pmc_sync_gallery(_PROJECT_ID, 'pmc_autologin=x', _CSRF, soup, image_list, tmp_path, 0)

    assert mock_open.call_count == 1
    req = mock_open.call_args[0][0]
    assert b'delete' in req.data


# ── 4. PMC.push ──────────────────────────────────────────────────────────────

def _push_responses():
    return [
        _make_response(_EDIT_HTML),
        _make_response({'status': 'success'}),
    ]


def test_push_sends_title_and_description(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {
        'name': 'CoolPack',
        'planetminecraft': {'id': _PROJECT_ID, 'resolution': 16, 'progress': 80},
    }
    with patch('urllib.request.urlopen', side_effect=_push_responses()) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='[b]Hello[/b]',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )

    update_req = mock_open.call_args_list[1][0][0]
    assert b'CoolPack' in update_req.data
    assert b'Hello' in update_req.data
    assert b'80' in update_req.data


def test_push_preserves_mc_version(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {'name': 'Pack', 'planetminecraft': {'id': _PROJECT_ID}}
    with patch('urllib.request.urlopen', side_effect=_push_responses()) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )

    update_req = mock_open.call_args_list[1][0][0]
    assert b'op1' in update_req.data
    assert b'1.21' in update_req.data


def test_push_maps_category(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {'name': 'Pack', 'planetminecraft': {'id': _PROJECT_ID, 'category': 'Realistic'}}
    with patch('urllib.request.urlopen', side_effect=_push_responses()) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )

    update_req = mock_open.call_args_list[1][0][0]
    assert b'25' in update_req.data  # Realistic = 25


def test_push_sets_download_link_to_modrinth(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {
        'name': 'Pack',
        'planetminecraft': {'id': _PROJECT_ID},
        'modrinth': {'slug': 'mypack'},
    }
    with patch('urllib.request.urlopen', side_effect=_push_responses()) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )

    update_req = mock_open.call_args_list[1][0][0]
    assert b'modrinth.com/resourcepack/mypack' in update_req.data


def test_push_sets_download_link_to_curseforge_when_no_modrinth(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {
        'name': 'Pack',
        'planetminecraft': {'id': _PROJECT_ID},
        'curseforge': {'slug': 'mypack-cf'},
    }
    with patch('urllib.request.urlopen', side_effect=_push_responses()) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )

    update_req = mock_open.call_args_list[1][0][0]
    assert b'curseforge.com/minecraft/texture-packs/mypack-cf' in update_req.data


def test_push_includes_modifies(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {
        'name': 'Pack',
        'planetminecraft': {'id': _PROJECT_ID, 'modifies': {'terrain': True, 'gui': True, 'mobs': False}},
    }
    with patch('urllib.request.urlopen', side_effect=_push_responses()) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )

    update_req = mock_open.call_args_list[1][0][0]
    assert b'32' in update_req.data   # terrain
    assert b'34' in update_req.data   # gui


def test_push_raises_system_exit_on_failure(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {'name': 'Pack', 'planetminecraft': {'id': _PROJECT_ID}}
    responses = [
        _make_response(_EDIT_HTML),
        _make_response({'status': 'error', 'message': 'bad request'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        with pytest.raises(SystemExit, match='PMC update failed'):
            PMC.push(
                project_id=_PROJECT_ID, config=config, description='',
                icon_path=icon, logo_path=None, banner_path=None,
                image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
            )


# ── 5. _run_pmc_native routing ───────────────────────────────────────────────

def test_run_push_uses_pmc_native_when_pmc_creds_present(push_env, run_puppy):
    import yaml as _yaml
    (push_env['project'] / 'puppy.yaml').write_text(
        _yaml.dump({
            'name': 'NeonGlow', 'pack': 'neonglow',
            'curseforge': {'slug': 'neonglow'},
            'modrinth': {'slug': 'neonglow'},
            'planetminecraft': {'id': _PROJECT_ID, 'slug': 'neonglow'},
        })
    )
    (push_env['home'] / 'auth.yaml').write_text(_yaml.dump({
        'modrinth': {'token': 'token123'},
        'curseforge': {'token': 'cf456', 'cookie': 'CobaltSession=fake'},
        'planetminecraft': 'pmc_autologin=test-cookie',
    }))

    called = []
    import puppy.syncer as syncer_mod
    orig = syncer_mod._run_pmc_native
    syncer_mod._run_pmc_native = lambda *a, **k: called.append(True)
    try:
        run_puppy('push', '--site', 'pmc')
    finally:
        syncer_mod._run_pmc_native = orig

    assert called


def test_run_pmc_native_auth_expired_raises_system_exit(tmp_path):
    project = Project(tmp_path, override_name='Pack', override_pack='pack')
    config = {'name': 'Pack', 'planetminecraft': {'id': _PROJECT_ID}}

    with patch('puppy.sites.planetminecraft._pmc_get_page', side_effect=AuthExpiredError(401, 'Expired')):
        with pytest.raises(SystemExit, match='PlanetMinecraft auth expired'):
            _run_pmc_native_real(project, config, tmp_path / 'icon.png', tmp_path, {}, _AUTH, 0)


def test_run_pmc_native_skips_gallery_when_images_false(tmp_path):
    project = Project(tmp_path, override_name='Pack', override_pack='pack')
    config = {
        'name': 'Pack',
        'planetminecraft': {'id': _PROJECT_ID},
        'images': [{'file': 'banner', 'description': 'A banner'}],
    }
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)

    push_calls = []

    def fake_push(self, **kwargs):
        push_calls.append(kwargs['image_list'])

    with patch.object(PMC.__class__, 'push', fake_push):
        _run_pmc_native_real(project, config, icon, tmp_path, {}, _AUTH, 0, images=False)

    assert push_calls[0] == []


def test_run_pmc_native_passes_image_list_when_images_true(tmp_path):
    project = Project(tmp_path, override_name='Pack', override_pack='pack')
    config = {
        'name': 'Pack',
        'planetminecraft': {'id': _PROJECT_ID},
        'images': [{'file': 'banner', 'description': 'A banner'}],
    }
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)

    push_calls = []

    def fake_push(self, **kwargs):
        push_calls.append(kwargs['image_list'])

    with patch.object(PMC.__class__, 'push', fake_push):
        _run_pmc_native_real(project, config, icon, tmp_path, {}, _AUTH, 0, images=True)

    assert push_calls[0] == config['images']
