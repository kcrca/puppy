import json
import zipfile
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from puppy.errors import AuthExpiredError, SiteError
from puppy.sites import MODRINTH
from puppy.sites.modrinth import _MR_API
from puppy.syncer import _run_mr as _run_mr_real
from puppy.puller import _run_mr_pull as _run_mr_pull_real


_AUTH = {'modrinth': {'token': 'test-token'}}
_PROJECT_ID = 'test-project-slug'


def _make_response(body: bytes | list | dict | None, status: int = 200):
    if body is None:
        encoded = b''
    elif isinstance(body, (dict, list)):
        encoded = json.dumps(body).encode()
    else:
        encoded = body
    resp = MagicMock()
    resp.read.return_value = encoded
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _make_http_error(code: int, body: str = ''):
    import io
    import urllib.error
    return urllib.error.HTTPError(url='', code=code, msg='', hdrs={}, fp=io.BytesIO(body.encode()))


# ── 1. upload_icon ───────────────────────────────────────────────────────────

def test_upload_icon_sends_patch_to_correct_endpoint():
    icon_bytes = b'PNGDATA'
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(None)
        MODRINTH.upload_icon(_PROJECT_ID, _AUTH, icon_bytes)

    req = mock_open.call_args[0][0]
    assert req.full_url == f'{_MR_API}/project/{_PROJECT_ID}/icon?ext=png'
    assert req.method == 'PATCH'
    assert req.get_header('Content-type') == 'image/png'
    assert req.get_header('Authorization') == 'test-token'
    assert req.data == icon_bytes


# ── 2. sync_gallery ──────────────────────────────────────────────────────────

def test_sync_gallery_deletes_removed_and_uploads_new():
    existing = [
        {'title': 'old-image.jpg', 'url': 'https://cdn.modrinth.com/old-image.jpg'},
        {'title': 'keep.jpg', 'url': 'https://cdn.modrinth.com/keep.jpg'},
    ]
    new_images = [
        {'filename': 'keep.jpg', 'data': b'IMGDATA', 'mime_type': 'image/jpeg'},
        {'filename': 'new-image.jpg', 'data': b'NEWDATA', 'mime_type': 'image/jpeg'},
    ]
    responses = [
        _make_response({'gallery': existing}),  # GET project (gallery embedded)
        _make_response(None),                   # DELETE old-image
        _make_response(None),                   # POST new-image
    ]

    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        MODRINTH.sync_gallery(_PROJECT_ID, _AUTH, new_images)

    calls = mock_open.call_args_list
    assert len(calls) == 3

    get_req = calls[0][0][0]
    assert f'project/{_PROJECT_ID}' in get_req.full_url
    assert 'gallery' not in get_req.full_url

    del_req = calls[1][0][0]
    assert del_req.method == 'DELETE'
    assert f'project/{_PROJECT_ID}/gallery' in del_req.full_url
    assert 'old-image.jpg' in del_req.full_url

    post_req = calls[2][0][0]
    assert post_req.method == 'POST'
    assert f'project/{_PROJECT_ID}/gallery' in post_req.full_url
    assert 'new-image.jpg' in post_req.full_url
    assert b'NEWDATA' == post_req.data


def test_sync_gallery_no_changes_when_images_match():
    existing = [{'title': 'keep.jpg', 'url': 'https://cdn.modrinth.com/keep.jpg'}]
    images = [{'filename': 'keep.jpg', 'data': b'DATA', 'mime_type': 'image/jpeg'}]
    with patch('urllib.request.urlopen', side_effect=[_make_response({'gallery': existing})]) as mock_open:
        MODRINTH.sync_gallery(_PROJECT_ID, _AUTH, images)
    assert mock_open.call_count == 1


# ── 3. update_project ────────────────────────────────────────────────────────

def test_update_project_sends_correct_json_fields():
    sc = {
        'name': 'My Pack',
        'summary': 'A cool pack',
        'resolution': '16x',
        'donation': {'patreon': 'https://patreon.com/me'},
        'discord': 'https://discord.gg/x',
    }
    config = {
        'name': 'My Pack',
        'license': 'MIT',
        'links': {'source': 'https://github.com/me/pack', 'issues': None},
    }

    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(None)
        MODRINTH.update_project(_PROJECT_ID, _AUTH, sc, '<description>', config)

    req = mock_open.call_args[0][0]
    assert req.full_url == f'{_MR_API}/project/{_PROJECT_ID}'
    assert req.method == 'PATCH'
    assert req.get_header('Content-type') == 'application/json'

    body = json.loads(req.data)
    assert body['title'] == 'My Pack'
    assert body['description'] == 'A cool pack'
    assert body['body'] == '<description>'
    assert body['categories'] == []
    assert body['additional_categories'] == ['16x']
    assert body['license_id'] == 'MIT'
    assert body['source_url'] == 'https://github.com/me/pack'
    assert body['issues_url'] is None
    assert body['discord_url'] == 'https://discord.gg/x'
    assert body['requested_status'] == 'approved'
    assert body['donation_urls'] == [{'id': 'patreon', 'platform': 'Patreon', 'url': 'https://patreon.com/me'}]
    assert body['client_side'] == 'required'
    assert body['server_side'] == 'unsupported'


def test_update_project_uses_configured_client_server_side():
    sc = {'name': 'My Mod', 'summary': 'A mod'}
    config = {'client_side': 'optional', 'server_side': 'required'}

    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(None)
        MODRINTH.update_project(_PROJECT_ID, _AUTH, sc, '', config)

    body = json.loads(mock_open.call_args[0][0].data)
    assert body['client_side'] == 'optional'
    assert body['server_side'] == 'required'


def test_upload_version_uses_loaders_from_config(tmp_path):
    zip_path = tmp_path / 'mymod-1.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    config = {
        'minecraft': '1.21',
        'pack': 'mymod',
        'modrinth': {'id': 'abc123', 'slug': 'mymod'},
        'loaders': ['fabric', 'quilt'],
    }
    real_upload = MODRINTH.__class__.upload_version
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response({'id': 'ver123'})
        real_upload(MODRINTH, 'abc123', _AUTH, zip_path, '1.0', config)

    req = mock_open.call_args[0][0]
    body_text = req.data.decode('latin-1')
    loaders_section = body_text.split('"loaders"')[1].split(']')[0]
    assert 'fabric' in loaders_section
    assert 'quilt' in loaders_section
    assert 'minecraft' not in loaders_section


def test_upload_version_defaults_to_minecraft_loader_for_pack(tmp_path):
    zip_path = tmp_path / 'mypack-1.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    config = {
        'minecraft': '1.21',
        'pack': 'mypack',
        'modrinth': {'id': 'abc123', 'slug': 'mypack'},
    }
    real_upload = MODRINTH.__class__.upload_version
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response({'id': 'ver123'})
        real_upload(MODRINTH, 'abc123', _AUTH, zip_path, '1.0', config)

    req = mock_open.call_args[0][0]
    body_text = req.data.decode('latin-1')
    assert '"loaders": ["minecraft"]' in body_text or '"loaders":["minecraft"]' in body_text


# ── 4. AuthExpiredError on 401 ───────────────────────────────────────────────

def test_update_project_401_raises_auth_expired():
    sc = {'name': 'X', 'summary': 'Y'}
    config = {}
    with patch('urllib.request.urlopen', side_effect=_make_http_error(401, 'Unauthorized')):
        with pytest.raises(AuthExpiredError) as exc_info:
            MODRINTH.update_project(_PROJECT_ID, _AUTH, sc, '', config)
    assert exc_info.value.code == 401


def test_upload_icon_non_401_raises_site_error():
    with patch('urllib.request.urlopen', side_effect=_make_http_error(404, 'Not Found')):
        with pytest.raises(SiteError) as exc_info:
            MODRINTH.upload_icon(_PROJECT_ID, _AUTH, b'PNGDATA')
    assert exc_info.value.code == 404


# ── 5. Integration: run_push routes to MR when MR token present ──────────

def test_run_push_when_mr_token_present(tmp_path, monkeypatch):
    root = tmp_path / 'neon'
    home = root / 'puppy'
    project_dir = home / 'MyPack'
    project_dir.mkdir(parents=True)

    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'puppy.yaml').write_text(yaml.dump({'projects': ['MyPack']}))
    (home / 'auth.yaml').write_text(yaml.dump({
        'modrinth': {'token': 'mr-token-abc'},
    }))
    (project_dir / 'puppy.yaml').write_text(yaml.dump({
        'name': 'MyPack',
        'pack': 'mypack',
        'modrinth': {'id': 'abc123', 'slug': 'mypack'},
        'planetminecraft': {'slug': 'mypack'},
    }))
    Image.new('RGB', (64, 64), color='blue').save(project_dir / 'icon.png')

    mr_calls = []

    def fake_mr(*args, **kwargs):
        mr_calls.append(args)

    monkeypatch.setattr('puppy.syncer._run_mr', fake_mr, raising=False)
    monkeypatch.chdir(project_dir)

    from puppy.config import ConfigSynthesizer
    from puppy.core import Project
    from puppy.syncer import run_push

    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=True)
    auth = {'modrinth': {'token': 'mr-token-abc'}}

    run_push(
        project=project,
        config=config,
        puppy_home=home,
        site='modrinth',
        version=None,
        pack=False,
        force=False,
        images=False,
        verbosity=0,
        auth=auth,
    )

    assert len(mr_calls) == 1
    called_config = mr_calls[0][1]
    assert called_config.get('modrinth', {}).get('id') == 'abc123'


# ── 5b. upload_version ───────────────────────────────────────────────────────

def test_upload_version_sends_multipart_with_correct_fields(tmp_path):
    zip_path = tmp_path / 'mypack-1.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    config = {
        'minecraft': '1.21',
        'pack': 'mypack',
        'modrinth': {'id': 'abc123', 'slug': 'mypack'},
    }
    # Call unpatched class method directly (autouse fixture patches the instance)
    real_upload = MODRINTH.__class__.upload_version
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response({'id': 'ver123'})
        real_upload(MODRINTH, 'abc123', _AUTH, zip_path, '1.0', config)

    req = mock_open.call_args[0][0]
    assert req.full_url == f'{_MR_API}/version'
    assert req.method == 'POST'
    assert 'multipart/form-data' in req.get_header('Content-type')
    assert b'application/zip' in req.data
    assert b'mypack-1.0.zip' in req.data
    body_text = req.data.decode('latin-1')
    assert '"game_versions": ["1.21"]' in body_text or '"game_versions":["1.21"]' in body_text
    assert '"loaders": ["minecraft"]' in body_text or '"loaders":["minecraft"]' in body_text
    assert '"version_number": "1.0"' in body_text or '"version_number":"1.0"' in body_text


def test_upload_version_in_push_pack(tmp_path, monkeypatch):
    root = tmp_path / 'neon'
    home = root / 'puppy'
    project_dir = home / 'MyPack'
    project_dir.mkdir(parents=True)

    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'puppy.yaml').write_text(yaml.dump({'projects': ['MyPack']}))
    (home / 'auth.yaml').write_text(yaml.dump({'modrinth': {'token': 'mr-token'}}))
    (project_dir / 'puppy.yaml').write_text(yaml.dump({
        'name': 'MyPack',
        'pack': 'mypack',
        'minecraft': '1.21',
        'modrinth': {'id': 'abc123', 'slug': 'mypack'},
    }))
    Image.new('RGB', (64, 64), color='blue').save(project_dir / 'icon.png')
    zip_path = project_dir / 'mypack-1.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')

    upload_calls = []
    monkeypatch.setattr('puppy.publisher.MODRINTH.upload_version', lambda *a, **k: upload_calls.append(a))
    monkeypatch.chdir(project_dir)

    from puppy.runner import run
    run(
        action='push',
        directory=project_dir,
        dry_run=False,
        verbosity=0,
        site='modrinth',
        version='1.0',
        pack=True,
        force=True,
    )

    assert len(upload_calls) == 1
    assert upload_calls[0][0] == 'abc123'   # project_id
    assert upload_calls[0][2].name == 'mypack-1.0.zip'  # zip_path


# ── 6. pull ──────────────────────────────────────────────────────────────────

def test_pull_fetches_project_and_writes_description(tmp_path):
    project_data = {
        'id': 'abc123', 'slug': 'mypack',
        'title': 'My Pack', 'description': 'A cool pack',
        'body': '# My Pack\nGreat stuff.',
        'icon_url': None, 'gallery': [],
        'license': {'id': 'MIT', 'name': 'MIT License', 'url': None},
        'issues_url': 'https://github.com/me/pack/issues',
        'source_url': 'https://github.com/me/pack',
        'wiki_url': None,
        'discord_url': 'https://discord.gg/x',
        'donation_urls': [{'id': 'patreon', 'platform': 'Patreon', 'url': 'https://patreon.com/me'}],
        'categories': ['16x', 'realistic'],
    }

    with patch('urllib.request.urlopen', side_effect=[_make_response(project_data)]):
        result = MODRINTH.pull('mypack', _AUTH, tmp_path, images=False)

    desc = tmp_path / 'modrinth' / 'description.md'
    assert desc.exists()
    assert '# My Pack' in desc.read_text()
    assert result['config']['name'] == 'My Pack'
    assert result['config']['summary'] == 'A cool pack'
    assert result['config']['license'] == 'MIT'
    assert result['config']['links'] == {'issues': 'https://github.com/me/pack/issues', 'source': 'https://github.com/me/pack'}
    assert result['config']['socials'] == {'discord': 'https://discord.gg/x'}
    assert result['modrinth']['id'] == 'abc123'
    assert result['modrinth']['slug'] == 'mypack'
    assert result['modrinth']['donation'] == {'patreon': 'https://patreon.com/me'}
    assert result['modrinth']['resolution'] == ['16x']
    assert result['modrinth']['category'] == ['realistic']


def test_pull_downloads_gallery_images(tmp_path):
    gallery = [
        {'url': 'https://cdn.modrinth.com/img1.jpg', 'title': 'img1.jpg', 'description': ''},
        {'url': 'https://cdn.modrinth.com/img2.jpg', 'title': 'img2.jpg', 'description': ''},
    ]
    project_data = {
        'id': 'abc123', 'slug': 'mypack',
        'title': 'My Pack', 'description': '',
        'body': '', 'icon_url': None, 'gallery': gallery,
    }
    responses = [
        _make_response(project_data),
        _make_response(b'IMG1DATA'),
        _make_response(b'IMG2DATA'),
    ]

    with patch('urllib.request.urlopen', side_effect=responses):
        MODRINTH.pull('mypack', _AUTH, tmp_path, images=True)

    assert (tmp_path / 'images' / 'img1.jpg').exists()
    assert (tmp_path / 'images' / 'img2.jpg').exists()


def test_run_pull_when_mr_token_present(tmp_path, monkeypatch):
    root = tmp_path / 'neon'
    home = root / 'puppy'
    project_dir = home / 'MyPack'
    project_dir.mkdir(parents=True)

    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'puppy.yaml').write_text(yaml.dump({'projects': ['MyPack']}))
    (home / 'auth.yaml').write_text(yaml.dump({'modrinth': {'token': 'mr-token-abc'}}))
    (project_dir / 'puppy.yaml').write_text(yaml.dump({
        'name': 'MyPack', 'pack': 'mypack',
        'modrinth': {'id': 'abc123', 'slug': 'mypack'},
    }))

    pull_calls = []

    monkeypatch.setattr('puppy.puller._run_mr_pull', lambda *a, **k: pull_calls.append(a))
    monkeypatch.chdir(project_dir)

    from puppy.config import ConfigSynthesizer
    from puppy.core import Project
    from puppy.puller import run_pull

    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=True)
    auth = {'modrinth': {'token': 'mr-token-abc'}}

    run_pull(
        project=project,
        config=config,
        auth=auth,
        site='modrinth',
        images=False,
        verbosity=0,
    )

    assert len(pull_calls) == 1


# ── push images / auth-expired ────────────────────────────────────────────────

def _mr_project(tmp_path):
    p = MagicMock()
    p.puppy_dir = tmp_path
    p.name = 'TestPack'
    return p


def test_run_mr_skips_gallery_when_images_false(tmp_path):
    with patch('puppy.syncer.MODRINTH.push') as mock_push:
        _run_mr_real(
            project=_mr_project(tmp_path),
            config={'modrinth': {'id': 'abc'}, 'images': [{'file': 'img.jpg', 'description': ''}]},
            icon=tmp_path / 'icon.png',
            puppy_dir=tmp_path,
            descriptions={},
            auth=_AUTH,
            verbosity=0,
            images=False,
        )
    assert mock_push.call_args.kwargs['image_list'] == []


def test_run_mr_passes_image_list_when_images_true(tmp_path):
    img_list = [{'file': 'img.jpg', 'description': ''}]
    with patch('puppy.syncer.MODRINTH.push') as mock_push:
        _run_mr_real(
            project=_mr_project(tmp_path),
            config={'modrinth': {'id': 'abc'}, 'images': img_list},
            icon=tmp_path / 'icon.png',
            puppy_dir=tmp_path,
            descriptions={},
            auth=_AUTH,
            verbosity=0,
            images=True,
        )
    assert mock_push.call_args.kwargs['image_list'] == img_list


def test_run_mr_auth_expired_raises_system_exit(tmp_path):
    with patch('puppy.syncer.MODRINTH.push', side_effect=AuthExpiredError(401, 'expired')):
        with pytest.raises(SystemExit, match='Modrinth auth expired'):
            _run_mr_real(
                project=_mr_project(tmp_path),
                config={'modrinth': {'id': 'abc'}},
                icon=tmp_path / 'icon.png',
                puppy_dir=tmp_path,
                descriptions={},
                auth=_AUTH,
                verbosity=0,
            )


# ── pull images / auth-expired ────────────────────────────────────────────────

def _mr_pull_result():
    return {'config': {'name': 'T', 'summary': '', 'images': []}, 'modrinth': {'id': 'abc', 'slug': 'mypack'}}


def test_run_mr_pull_images_forced_when_no_image_info(tmp_path):
    (tmp_path / 'puppy.yaml').write_text('name: T\npack: t\nmodrinth:\n  id: abc\n  slug: mypack\n')
    pull_calls = []
    with patch('puppy.puller.MODRINTH.pull', side_effect=lambda **kw: (pull_calls.append(kw), _mr_pull_result())[1]):
        _run_mr_pull_real(
            project=_mr_project(tmp_path),
            config={'modrinth': {'id': 'abc', 'slug': 'mypack'}},
            auth=_AUTH,
            site='modrinth',
            images=False,
            verbosity=0,
        )
    assert pull_calls[0]['images'] is True


def test_run_mr_pull_images_skipped_when_info_exists(tmp_path):
    (tmp_path / 'puppy.yaml').write_text('name: T\npack: t\nmodrinth:\n  id: abc\n  slug: mypack\n')
    (tmp_path / 'images.yaml').write_text('[]\n')
    pull_calls = []
    with patch('puppy.puller.MODRINTH.pull', side_effect=lambda **kw: (pull_calls.append(kw), _mr_pull_result())[1]):
        _run_mr_pull_real(
            project=_mr_project(tmp_path),
            config={'modrinth': {'id': 'abc', 'slug': 'mypack'}},
            auth=_AUTH,
            site='modrinth',
            images=False,
            verbosity=0,
        )
    assert pull_calls[0]['images'] is False


def test_run_mr_pull_images_true_fetches_even_when_info_exists(tmp_path):
    (tmp_path / 'puppy.yaml').write_text('name: T\npack: t\nmodrinth:\n  id: abc\n  slug: mypack\n')
    (tmp_path / 'images.yaml').write_text('[]\n')
    pull_calls = []
    with patch('puppy.puller.MODRINTH.pull', side_effect=lambda **kw: (pull_calls.append(kw), _mr_pull_result())[1]):
        _run_mr_pull_real(
            project=_mr_project(tmp_path),
            config={'modrinth': {'id': 'abc', 'slug': 'mypack'}},
            auth=_AUTH,
            site='modrinth',
            images=True,
            verbosity=0,
        )
    assert pull_calls[0]['images'] is True


def test_run_mr_pull_auth_expired_raises_system_exit(tmp_path):
    with patch('puppy.puller.MODRINTH.pull', side_effect=AuthExpiredError(401, 'expired')):
        with pytest.raises(SystemExit, match='Modrinth auth expired'):
            _run_mr_pull_real(
                project=_mr_project(tmp_path),
                config={'modrinth': {'id': 'abc', 'slug': 'mypack'}},
                auth=_AUTH,
                site='modrinth',
                images=False,
                verbosity=0,
            )


# ── publisher auth-expired ────────────────────────────────────────────────────

def test_upload_pack_mr_skips_when_already_current(tmp_path, monkeypatch):
    from puppy.publisher import upload_pack
    from puppy.core import Project
    zip_path = tmp_path / 'pack-1.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    project = Project(tmp_path, override_name='T', override_pack='pack')
    config = {'minecraft': '1.21', 'modrinth': {'id': 'abc', 'slug': 'mypack'}}

    upload_calls = []
    monkeypatch.setattr('puppy.publisher.MODRINTH.needs_upload', lambda *a, **k: False)
    monkeypatch.setattr('puppy.publisher.MODRINTH.upload_version', lambda *a, **k: upload_calls.append(a))
    upload_pack(
        project=project,
        config=config,
        site='modrinth',
        version='1.0',
        force=False,
        verbosity=0,
        auth={'modrinth': {'token': 'tok'}},
    )
    assert upload_calls == []


def test_upload_pack_mr_auth_expired_raises_system_exit(tmp_path, monkeypatch):
    from puppy.publisher import upload_pack
    from puppy.core import Project
    zip_path = tmp_path / 'pack-1.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    project = Project(tmp_path, override_name='T', override_pack='pack')
    config = {'minecraft': '1.21', 'modrinth': {'id': 'abc', 'slug': 'mypack'}}

    def raise_auth(*a, **k):
        raise AuthExpiredError(401, 'token expired')

    monkeypatch.setattr('puppy.publisher.MODRINTH.upload_version', raise_auth)
    with pytest.raises(SystemExit, match='Modrinth auth expired'):
        upload_pack(
            project=project,
            config=config,
            site='modrinth',
            version='1.0',
            force=True,
            verbosity=0,
            auth={'modrinth': {'token': 'tok'}},
        )
