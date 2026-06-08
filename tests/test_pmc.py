import io
import json
import zipfile
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from bs4 import BeautifulSoup
from PIL import Image

from puppy.core import Project
from puppy.errors import AuthExpiredError
from puppy.sites import PMC
from puppy.puller import _run_pmc_pull as _run_pmc_pull_real
from puppy.syncer import _run_pmc as _run_pmc_real


_AUTH = {'planetminecraft': {'cookie': 'pmc_autologin=test-cookie'}}
_PROJECT_ID = 999
_PACK = 'neonglow'
_VERSION = '1.0.0'


@pytest.fixture(autouse=True)
def _no_pmc_description(monkeypatch):
    monkeypatch.setattr('puppy.sites.planetminecraft._pmc_fetch_description', lambda *a, **k: None)


@pytest.fixture
def push_pack_env(project_env):
    source = project_env['project']
    Image.new('RGB', (64, 64), color='blue').save(source / 'icon.png')
    with zipfile.ZipFile(source / f'{_PACK}-{_VERSION}.zip', 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    return project_env

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


def test_push_uses_planetminecraft_title_when_set(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {
        'name': 'CoolPack',
        'title': 'CoolPack: Special Edition',
        'planetminecraft': {'id': _PROJECT_ID},
    }
    with patch('urllib.request.urlopen', side_effect=_push_responses()) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )

    update_req = mock_open.call_args_list[1][0][0]
    assert b'CoolPack: Special Edition' in update_req.data
    assert b'CoolPack\r\n' not in update_req.data


def test_push_falls_back_to_name_when_title_absent(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    config = {
        'name': 'CoolPack',
        'planetminecraft': {'id': _PROJECT_ID},
    }
    with patch('urllib.request.urlopen', side_effect=_push_responses()) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )

    update_req = mock_open.call_args_list[1][0][0]
    assert b'CoolPack' in update_req.data


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


def test_push_bedrock_pack_uses_bedrock_op1(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    html = _EDIT_HTML.replace(
        '<select id="op1"><option value="1.21" selected>1.21</option></select>',
        '<select id="op1"><option value="1.21" selected>1.21</option><option value="bedrock-val">Minecraft Bedrock</option></select>',
    )
    responses = [_make_response(html), _make_response({'status': 'success'})]
    config = {'name': 'Pack', 'planetminecraft': {'id': _PROJECT_ID, 'bedrock': True}}
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )
    update_req = mock_open.call_args_list[1][0][0]
    assert b'bedrock-val' in update_req.data
    assert b'1.21\r\n' not in update_req.data


def test_push_bedrock_world_sends_platform_field(tmp_path):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (64, 64)).save(icon)
    responses = [_make_response(_EDIT_HTML), _make_response({'status': 'success'})]
    config = {
        'name': 'Pack', 'project_type': 'world',
        'planetminecraft': {'id': _PROJECT_ID, 'bedrock': True},
    }
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        PMC.push(
            project_id=_PROJECT_ID, config=config, description='',
            icon_path=icon, logo_path=None, banner_path=None,
            image_list=[], images_dir=tmp_path, auth=_AUTH, verbosity=0,
        )
    update_req = mock_open.call_args_list[1][0][0]
    assert b'platform' in update_req.data
    assert b'2' in update_req.data


# ── 5. _run_pmc routing ──────────────────────────────────────────────────────

def test_run_push_when_pmc_creds_present(push_env, run_puppy):
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
        'planetminecraft': {'cookie': 'pmc_autologin=test-cookie'},
    }))

    called = []
    import puppy.syncer as syncer_mod
    orig = syncer_mod._run_pmc
    syncer_mod._run_pmc = lambda *a, **k: called.append(True)
    try:
        run_puppy('push', '--site', 'pmc')
    finally:
        syncer_mod._run_pmc = orig

    assert called


def test_run_pmc_auth_expired_raises_system_exit(tmp_path):
    project = Project(tmp_path, override_name='Pack', override_pack='pack')
    config = {'name': 'Pack', 'planetminecraft': {'id': _PROJECT_ID}}

    with patch('puppy.sites.planetminecraft._pmc_get_page', side_effect=AuthExpiredError(401, 'Expired')):
        with pytest.raises(SystemExit, match='PlanetMinecraft auth expired'):
            _run_pmc_real(project, config, tmp_path / 'icon.png', tmp_path, {}, _AUTH, 0)


def test_run_pmc_skips_gallery_when_images_false(tmp_path):
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
        _run_pmc_real(project, config, icon, tmp_path, {}, _AUTH, 0, images=False)

    assert push_calls[0] == []


def test_run_pmc_passes_image_list_when_images_true(tmp_path):
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
        _run_pmc_real(project, config, icon, tmp_path, {}, _AUTH, 0, images=True)

    assert push_calls[0] == config['images']


# ── 6. PMC.pull ───────────────────────────────────────────────────────────────

_PULL_HTML = '''
<meta id="core-csrf-token" content="csrf-token-abc">
<input name="title" value="Test Pack">
<input name="youtube" value="dQw4w9WgXcQ">
<select id="folder_id[]"><option value="25" selected>Realistic</option></select>
<select id="op0"><option value="1" selected>16x</option></select>
<input id="progress" value="75">
<input name="credit" value="Some Guy">
<div id="main_folder_modified">
  <div class="folder-item"><input type="checkbox" checked><label>Terrain</label></div>
  <div class="folder-item"><input type="checkbox"><label>GUI</label></div>
</div>
<div id="item_tags">
  <span class="tag">16x</span>
  <span class="tag">fantasy</span>
</div>
<ul class="image_list">
  <li class="thumbnail" data-full-filename="/files/123-cool-banner_s.jpg" data-caption="cool_banner - Cool banner"></li>
  <li class="thumbnail" data-full-filename="/files/thumb.jpg" data-caption="Project Thumbnail"></li>
  <li class="thumbnail" data-full-filename="/files/logo.jpg" data-caption="Project Logo"></li>
</ul>
'''


def test_pull_scrapes_category_resolution_progress_credit(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    pmc = result['planetminecraft']
    assert pmc['category'] == 'Realistic'
    assert pmc['resolution'] == 16
    assert pmc['progress'] == 75
    assert pmc['credit'] == 'Some Guy'


def test_pull_scrapes_modifies(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    modifies = result['planetminecraft']['modifies']
    assert modifies['terrain'] is True
    assert modifies['gui'] is False


def test_pull_scrapes_tags(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    assert result['planetminecraft']['tags'] == ['16x', 'fantasy']


def test_pull_scrapes_name_and_video(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    assert result['config']['name'] == 'Test Pack'
    assert result['config']['video'] == 'dQw4w9WgXcQ'


def test_pull_detects_bedrock_pack(tmp_path):
    html = _PULL_HTML + '<select id="op1"><option value="bedrock-val" selected>Minecraft Bedrock</option></select>'
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(html)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)
    assert result['planetminecraft'].get('bedrock') is True


def test_pull_no_bedrock_flag_for_java_pack(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)
    assert 'bedrock' not in result['planetminecraft']


def test_pull_detects_bedrock_world(tmp_path):
    html = _PULL_HTML + '<input type="checkbox" name="platform" value="2" checked>'
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(html)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False, project_type='world')
    assert result['planetminecraft'].get('bedrock') is True


def test_pull_no_bedrock_flag_for_java_world(tmp_path):
    html = _PULL_HTML + '<input type="checkbox" name="platform" value="2">'
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(html)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False, project_type='world')
    assert 'bedrock' not in result['planetminecraft']


def test_pull_includes_image_entries_skipping_special(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    entries = result['config']['images']
    assert len(entries) == 1
    assert entries[0]['file'] == 'cool_banner'   # URL-derived: 123-cool-banner_s → cool_banner
    assert entries[0]['description'] == 'Cool banner'


def test_pull_downloads_images_and_thumbnail_and_logo(tmp_path):
    img_bytes = b'FAKEIMG'
    thumb_bytes = b'THUMB'
    logo_bytes = b'LOGO'
    responses = [
        _make_response(_PULL_HTML),       # edit page
        _make_response(thumb_bytes),      # Project Thumbnail → banner.png
        _make_response(logo_bytes),       # Project Logo → logo.png
        _make_response(img_bytes),        # gallery image
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=True, verbosity=0)

    assert (tmp_path / 'banner.png').read_bytes() == thumb_bytes
    assert (tmp_path / 'logo.png').read_bytes() == logo_bytes
    assert (tmp_path / 'images' / 'cool_banner.png').read_bytes() == img_bytes


def test_pull_skips_thumbnail_if_banner_exists(tmp_path):
    (tmp_path / 'banner.png').write_bytes(b'EXISTING')
    responses = [
        _make_response(_PULL_HTML),
        _make_response(b'LOGO'),    # logo download (thumbnail skipped)
        _make_response(b'IMG'),     # gallery
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=True, verbosity=0)

    assert (tmp_path / 'banner.png').read_bytes() == b'EXISTING'


def test_pull_skips_download_when_images_false(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    assert not (tmp_path / 'images').exists()
    assert not (tmp_path / 'banner.png').exists()
    assert mock_open.call_count == 1


def test_pull_includes_project_id(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        result = PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    assert result['planetminecraft']['id'] == _PROJECT_ID


def test_pull_writes_description_bbcode(tmp_path, monkeypatch):
    monkeypatch.setattr(
        'puppy.sites.planetminecraft._pmc_fetch_description',
        lambda *a, **k: '[b]Hello[/b]',
    )
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    assert (tmp_path / 'description.bbcode').read_text() == '[b]Hello[/b]'


def test_pull_no_description_file_when_unavailable(tmp_path):
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(_PULL_HTML)
        PMC.pull(project_id=_PROJECT_ID, auth=_AUTH, puppy_dir=tmp_path, images=False)

    assert not (tmp_path / 'description.bbcode').exists()


# ── 7. _run_pmc_pull routing ─────────────────────────────────────────────────

def test_run_pull_when_pmc_creds_present(push_env, run_puppy):
    import yaml as _yaml
    (push_env['project'] / 'puppy.yaml').write_text(
        _yaml.dump({
            'name': 'NeonGlow', 'pack': 'neonglow',
            'planetminecraft': {'id': _PROJECT_ID, 'slug': 'neonglow'},
        })
    )
    (push_env['home'] / 'auth.yaml').write_text(_yaml.dump({
        'planetminecraft': {'cookie': 'pmc_autologin=test-cookie'},
    }))

    called = []
    import puppy.puller as puller_mod
    orig = puller_mod._run_pmc_pull
    puller_mod._run_pmc_pull = lambda *a, **k: called.append(True)
    try:
        run_puppy('pull', '--site', 'pmc')
    finally:
        puller_mod._run_pmc_pull = orig

    assert called


def test_run_pmc_pull_images_forced_when_no_image_info(tmp_path):
    project = Project(tmp_path, override_name='Pack', override_pack='pack')
    config = {'planetminecraft': {'id': _PROJECT_ID}}

    pull_calls = []

    def fake_pull(self, project_id, auth, puppy_dir, images, verbosity, project_type='pack'):
        pull_calls.append(images)
        return {'config': {}, 'planetminecraft': {'id': project_id}}

    with patch.object(PMC.__class__, 'pull', fake_pull):
        _run_pmc_pull_real(project, config, _AUTH, None, False, 0)

    # No images.yaml exists → images forced True
    assert pull_calls[0] is True


def test_run_pmc_pull_images_skipped_when_info_exists(tmp_path):
    project = Project(tmp_path, override_name='Pack', override_pack='pack')
    config = {'planetminecraft': {'id': _PROJECT_ID}}
    (tmp_path / 'images.yaml').write_text('[]')

    pull_calls = []

    def fake_pull(self, project_id, auth, puppy_dir, images, verbosity, project_type='pack'):
        pull_calls.append(images)
        return {'config': {}, 'planetminecraft': {'id': project_id}}

    with patch.object(PMC.__class__, 'pull', fake_pull):
        _run_pmc_pull_real(project, config, _AUTH, None, False, 0)

    assert pull_calls[0] is False


def test_run_pmc_pull_images_true_fetches_even_when_info_exists(tmp_path):
    project = Project(tmp_path, override_name='Pack', override_pack='pack')
    config = {'planetminecraft': {'id': _PROJECT_ID}}
    (tmp_path / 'images.yaml').write_text('[]')

    pull_calls = []

    def fake_pull(self, project_id, auth, puppy_dir, images, verbosity, project_type='pack'):
        pull_calls.append(images)
        return {'config': {}, 'planetminecraft': {'id': project_id}}

    with patch.object(PMC.__class__, 'pull', fake_pull):
        _run_pmc_pull_real(project, config, _AUTH, None, True, 0)

    assert pull_calls[0] is True


def test_run_pmc_pull_auth_expired_raises_system_exit(tmp_path):
    project = Project(tmp_path, override_name='Pack', override_pack='pack')
    config = {'planetminecraft': {'id': _PROJECT_ID}}

    with patch('puppy.sites.planetminecraft._pmc_get_page', side_effect=AuthExpiredError(401, 'Expired')):
        with pytest.raises(SystemExit, match='PlanetMinecraft auth expired'):
            _run_pmc_pull_real(project, config, _AUTH, None, False, 0)


# ── 8. PMC.submit_log ────────────────────────────────────────────────────────

def test_submit_log_posts_correct_fields():
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.side_effect = [
            _make_response(_EDIT_HTML),
            _make_response({'status': 'success'}),
        ]
        real_submit = PMC.__class__.submit_log
        real_submit(PMC, _PROJECT_ID, _AUTH, '1.2.3', {'changelog': 'New stuff'})

    log_req = mock_open.call_args_list[1][0][0]
    assert b'log_title' in log_req.data
    assert b'1.2.3' in log_req.data
    assert b'New stuff' in log_req.data
    assert b'public/resource/manage' in log_req.data
    assert b'SAVE LOG' in log_req.data


def test_submit_log_raises_on_failure():
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.side_effect = [
            _make_response(_EDIT_HTML),
            _make_response({'status': 'error', 'feedback': 'unknown error'}),
        ]
        with pytest.raises(SystemExit, match='failed to submit version log'):
            PMC.__class__.submit_log(PMC, _PROJECT_ID, _AUTH, '1.2.3', {})


def test_submit_log_raises_rate_limit_message():
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.side_effect = [
            _make_response(_EDIT_HTML),
            _make_response({'status': 'error', 'feedback': 'Hit current daily update limit'}),
        ]
        with pytest.raises(SystemExit, match='daily update limit'):
            PMC.__class__.submit_log(PMC, _PROJECT_ID, _AUTH, '1.2.3', {})


def test_submit_log_auth_expired_raises_system_exit():
    with patch('puppy.sites.planetminecraft._pmc_get_page', side_effect=AuthExpiredError(401, 'Expired')):
        with pytest.raises(AuthExpiredError):
            PMC.__class__.submit_log(PMC, _PROJECT_ID, _AUTH, '1.2.3', {})


# ── 9. push --pack PMC routing ───────────────────────────────────────────────

def test_upload_pack_pmc_when_pmc_creds_present(push_pack_env, run_puppy, monkeypatch):
    source = push_pack_env['project']
    (source / 'puppy.yaml').write_text(
        yaml.dump({
            'name': 'NeonGlow', 'pack': 'neonglow', 'minecraft': '1.20',
            'curseforge': {'id': 111, 'slug': 'neonglow'},
            'modrinth': {'id': 'abc123', 'slug': 'neonglow'},
            'planetminecraft': {'id': _PROJECT_ID, 'slug': 'neonglow'},
        })
    )
    (push_pack_env['home'] / 'auth.yaml').write_text(yaml.dump({
        'modrinth': {'token': 'token123'},
        'curseforge': {'token': 'cf456', 'cookie': 'CobaltSession=fake'},
        'planetminecraft': {'cookie': 'pmc_autologin=test-cookie'},
    }))

    called = []
    monkeypatch.setattr('puppy.publisher.PMC.submit_log', lambda *a, **k: called.append(True))
    run_puppy('push', '--pack', '--force', '--version', '1.0.0', '--site', 'pmc')
    assert called


def test_upload_pack_pmc_skips_when_already_current(push_pack_env, run_puppy, monkeypatch):
    source = push_pack_env['project']
    (source / 'puppy.yaml').write_text(
        yaml.dump({
            'name': 'NeonGlow', 'pack': 'neonglow', 'minecraft': '1.20',
            'planetminecraft': {'id': _PROJECT_ID, 'slug': 'neonglow'},
        })
    )
    (push_pack_env['home'] / 'auth.yaml').write_text(yaml.dump({
        'planetminecraft': {'cookie': 'pmc_autologin=test-cookie'},
    }))
    state = {'planetminecraft': {'version': '1.0.0'}}
    (source / '.publish_state.yaml').write_text(yaml.dump(state))

    called = []
    monkeypatch.setattr('puppy.publisher.PMC.submit_log', lambda *a, **k: called.append(True))
    run_puppy('push', '--pack', '--version', '1.0.0', '--site', 'pmc')
    assert not called


def test_upload_pack_pmc_auth_expired_raises_system_exit(push_pack_env, run_puppy, monkeypatch):
    source = push_pack_env['project']
    (source / 'puppy.yaml').write_text(
        yaml.dump({
            'name': 'NeonGlow', 'pack': 'neonglow', 'minecraft': '1.20',
            'planetminecraft': {'id': _PROJECT_ID, 'slug': 'neonglow'},
        })
    )
    (push_pack_env['home'] / 'auth.yaml').write_text(yaml.dump({
        'planetminecraft': {'cookie': 'pmc_autologin=test-cookie'},
    }))
    monkeypatch.setattr(
        'puppy.publisher.PMC.submit_log',
        lambda *a, **k: (_ for _ in ()).throw(AuthExpiredError(401, 'Expired')),
    )
    result = run_puppy('push', '--pack', '--force', '--version', '1.0.0', '--site', 'pmc')
    assert result == 'PlanetMinecraft auth expired (HTTP 401) — run: puppy auth --site pmc'
