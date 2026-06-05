import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml
from PIL import Image

from puppy.errors import AuthExpiredError, SiteError
from puppy.sites import CURSEFORGE, _CF_DASH, _CF_API


_AUTH = {
    'curseforge': {
        'token': 'test-token',
        'cookie': 'CobaltSession=test-cookie',
    }
}
_PROJECT_ID = 12345


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
    import urllib.error
    err = urllib.error.HTTPError(url='', code=code, msg='', hdrs={}, fp=io.BytesIO(body.encode()))
    return err


# ── 1. update_description ────────────────────────────────────────────────────

def test_update_description_sends_correct_html():
    html = '<p>Hello world</p>'
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response({'ok': True})
        CURSEFORGE.update_description(_PROJECT_ID, _AUTH, html)

    req = mock_open.call_args[0][0]
    assert req.full_url == f'{_CF_DASH}/projects/description/{_PROJECT_ID}'
    assert req.method == 'PUT'
    assert req.get_header('Content-type') == 'application/json'
    assert req.get_header('Cookie') == 'CobaltSession=test-cookie'
    body = json.loads(req.data)
    assert body == {'description': html, 'descriptionType': 1}


# ── 2. upload_icon ───────────────────────────────────────────────────────────

def test_upload_icon_sends_multipart_to_correct_endpoint():
    icon_bytes = b'PNGDATA'
    with patch('urllib.request.urlopen') as mock_open:
        mock_open.return_value = _make_response(b'https://cf.example.com/avatar.png')
        CURSEFORGE.upload_icon(_PROJECT_ID, _AUTH, icon_bytes)

    req = mock_open.call_args[0][0]
    assert req.full_url == f'{_CF_DASH}/projects/{_PROJECT_ID}/upload-avatar'
    assert req.method == 'POST'
    content_type = req.get_header('Content-type')
    assert content_type.startswith('multipart/form-data; boundary=')
    body = req.data
    assert b'name="file"' in body
    assert b'name="id"' in body
    assert str(_PROJECT_ID).encode() in body
    assert icon_bytes in body


# ── 3. sync_gallery ──────────────────────────────────────────────────────────

def test_sync_gallery_deletes_removed_and_uploads_new():
    existing = [
        {'id': 1, 'title': 'old-image.jpg'},
        {'id': 2, 'title': 'keep.jpg'},
    ]
    new_images = [
        {'filename': 'keep.jpg', 'data': b'IMGDATA', 'mime_type': 'image/jpeg'},
        {'filename': 'new-image.jpg', 'data': b'NEWDATA', 'mime_type': 'image/jpeg'},
    ]
    responses = [
        _make_response(existing),       # GET existing gallery
        _make_response(None),           # DELETE old-image
        _make_response({'id': 50}),     # POST upload new-image
        _make_response(None),           # PUT metadata
    ]

    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        CURSEFORGE.sync_gallery(_PROJECT_ID, _AUTH, new_images)

    calls = mock_open.call_args_list
    assert len(calls) == 4

    get_req = calls[0][0][0]
    assert 'image-attachments/image' in get_req.full_url
    assert str(_PROJECT_ID) in get_req.full_url

    delete_req = calls[1][0][0]
    assert delete_req.method == 'DELETE'
    assert 'image-attachments' in delete_req.full_url
    assert '1/1' in delete_req.full_url

    post_req = calls[2][0][0]
    assert post_req.method == 'POST'
    assert f'image-attachments/image/{_PROJECT_ID}' in post_req.full_url
    assert b'new-image.jpg' in post_req.data

    put_req = calls[3][0][0]
    assert put_req.method == 'PUT'
    assert 'image-attachments/50' in put_req.full_url


def test_sync_gallery_no_changes_when_images_match():
    existing = [{'id': 1, 'title': 'keep.jpg'}]
    images = [{'filename': 'keep.jpg', 'data': b'DATA', 'mime_type': 'image/jpeg'}]
    responses = [_make_response(existing)]

    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        CURSEFORGE.sync_gallery(_PROJECT_ID, _AUTH, images)

    assert mock_open.call_count == 1


# ── 4. upload_file ───────────────────────────────────────────────────────────

def test_upload_file_sends_correct_multipart_with_metadata(tmp_path):
    zip_path = tmp_path / 'pack-1.0.0.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')

    config = {
        'minecraft': '1.21',
        'curseforge': {'slug': 'mypack'},
        'pack': 'mypack',
    }

    game_versions_resp = [
        {'id': 10550, 'name': '1.21', 'gameVersionTypeID': 615},
        {'id': 10500, 'name': '1.20.4', 'gameVersionTypeID': 615},
    ]
    responses = [
        _make_response(game_versions_resp),  # GET /api/game/versions
        _make_response({'id': 99}),           # POST upload-file
    ]

    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        CURSEFORGE.upload_file(_PROJECT_ID, _AUTH, zip_path, '1.0.0', config)

    calls = mock_open.call_args_list
    ver_req = calls[0][0][0]
    assert 'game/versions' in ver_req.full_url
    assert ver_req.get_header('X-api-token') == 'test-token'

    req = calls[1][0][0]
    assert req.full_url == f'{_CF_API}/projects/{_PROJECT_ID}/upload-file'
    assert req.method == 'POST'
    assert req.get_header('X-api-token') == 'test-token'

    body = req.data
    assert b'metadata' in body
    assert b'pack-1.0.0.zip' in body

    boundary_line = body.split(b'\r\n')[0]
    boundary = boundary_line[2:]
    parts = body.split(b'--' + boundary)
    metadata_part = next(p for p in parts if b'name="metadata"' in p)
    metadata_json_start = metadata_part.index(b'\r\n\r\n') + 4
    metadata = json.loads(metadata_part[metadata_json_start:].rstrip(b'\r\n'))
    assert metadata['displayName'] == 'mypack v1.0.0'
    assert metadata['releaseType'] == 'release'
    assert metadata['changelogType'] == 'markdown'
    assert metadata['gameVersions'] == [10550]


# ── 5. update_details ────────────────────────────────────────────────────────

def test_update_details_sends_correct_json_fields():
    sc = {
        'name': 'My Pack',
        'summary': 'A cool pack',
        'license': 'MIT License',
        'socials': {'discord': 'https://discord.gg/x', 'website': None},
        'links': {'source': 'https://github.com/x/y', 'wiki': None},
    }

    responses = [
        _make_response({'ok': True}),  # update-details
        _make_response({'ok': True}),  # project-license
        _make_response({'ok': True}),  # project-source
    ]

    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        CURSEFORGE.update_details(_PROJECT_ID, _AUTH, sc)

    calls = mock_open.call_args_list
    assert len(calls) == 3

    details_req = calls[0][0][0]
    assert f'projects/{_PROJECT_ID}/update-details' in details_req.full_url
    assert details_req.method == 'PUT'
    details_body = json.loads(details_req.data)
    assert details_body['name'] == 'My Pack'
    assert details_body['summary'] == 'A cool pack'
    assert details_body['allowComments'] is True
    assert details_body['enableProjectPages'] is False
    assert details_body['links'] == [{'type': 2, 'url': 'https://discord.gg/x'}]  # discord=2, website=None filtered

    license_req = calls[1][0][0]
    assert f'project-license/{_PROJECT_ID}/update' in license_req.full_url
    assert license_req.method == 'PUT'
    license_body = json.loads(license_req.data)
    assert license_body['licenseId'] == 4  # MIT License

    source_req = calls[2][0][0]
    assert f'project-source/{_PROJECT_ID}/update' in source_req.full_url
    assert source_req.method == 'PUT'
    source_body = json.loads(source_req.data)
    assert source_body['sourceHostUrl'] == 'https://github.com/x/y'
    assert source_body['sourceHost'] == 3
    assert source_body['packagerMode'] == 1


# ── 6. AuthExpiredError on 403 ───────────────────────────────────────────────

def test_update_description_403_raises_auth_expired():
    with patch('urllib.request.urlopen', side_effect=_make_http_error(403, 'Forbidden')):
        with pytest.raises(AuthExpiredError) as exc_info:
            CURSEFORGE.update_description(_PROJECT_ID, _AUTH, '<p>test</p>')
    assert exc_info.value.code == 403


def test_update_description_401_raises_auth_expired():
    with patch('urllib.request.urlopen', side_effect=_make_http_error(401, 'Unauthorized')):
        with pytest.raises(AuthExpiredError) as exc_info:
            CURSEFORGE.update_description(_PROJECT_ID, _AUTH, '<p>test</p>')
    assert exc_info.value.code == 401


def test_upload_file_401_raises_auth_expired(tmp_path):
    zip_path = tmp_path / 'pack.zip'
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    config = {'curseforge': {'slug': 'p'}, 'pack': 'p', 'minecraft': '1.21'}
    with patch('urllib.request.urlopen', side_effect=_make_http_error(401, 'Unauthorized')):
        with pytest.raises(AuthExpiredError):
            CURSEFORGE.upload_file(_PROJECT_ID, _AUTH, zip_path, '1.0', config)


# ── 7. Integration: run_push uses native path when CF token present ──────────

def test_run_push_uses_native_path_when_cf_token_present(tmp_path, monkeypatch):
    root = tmp_path / 'neon'
    home = root / 'puppy'
    project_dir = home / 'MyPack'
    project_dir.mkdir(parents=True)

    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'puppy.yaml').write_text(yaml.dump({'projects': ['MyPack']}))
    (home / 'auth.yaml').write_text(yaml.dump({
        'modrinth': {'token': 'token123'},
        'curseforge': {'token': 'cf456', 'cookie': 'CobaltSession=fake'},
    }))
    (project_dir / 'puppy.yaml').write_text(yaml.dump({
        'name': 'MyPack',
        'pack': 'mypack',
        'curseforge': {'id': 99, 'slug': 'mypack'},
        'modrinth': {'slug': 'mypack'},
        'planetminecraft': {'slug': 'mypack'},
    }))
    Image.new('RGB', (64, 64), color='blue').save(project_dir / 'icon.png')

    worker_dir = tmp_path / 'PackUploader'
    worker_dir.mkdir()
    (worker_dir / 'settings.json').write_text(json.dumps({
        'ewan': False, 'modrinth': {}, 'curseforge': {}, 'planetminecraft': {},
        'templateDefaults': {},
    }))

    cf_native_calls = []

    def fake_cf_native(*args, **kwargs):
        cf_native_calls.append(args)

    monkeypatch.setattr('puppy.syncer._run_cf_native', fake_cf_native, raising=False)
    monkeypatch.setattr('puppy.syncer._run_worker', lambda *a, **k: None)
    monkeypatch.chdir(project_dir)

    from puppy.config import ConfigSynthesizer
    from puppy.core import Project
    from puppy.syncer import run_push

    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=True)
    auth = {'curseforge': {'token': 'cf456', 'cookie': 'CobaltSession=fake'}, 'modrinth': {'token': 'token123'}}

    run_push(
        project=project,
        config=config,
        worker_dir=worker_dir,
        puppy_home=home,
        site='curseforge',
        version=None,
        pack=False,
        force=False,
        images=False,
        verbosity=0,
        auth=auth,
    )

    assert len(cf_native_calls) == 1
    # args: project, config, icon, puppy_dir, descriptions, auth, verbosity
    called_config = cf_native_calls[0][1]
    assert called_config.get('curseforge', {}).get('id') == 99
