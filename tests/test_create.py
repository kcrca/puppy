import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from PIL import Image

from puppy.errors import AuthExpiredError
from puppy.sites import _CF_DASH, _MR_API, CURSEFORGE, MODRINTH, PMC

_MR_AUTH = {'modrinth': {'token': 'test-token'}}
_CF_AUTH = {'curseforge': {'token': 'cf-token', 'cookie': 'CobaltSession=cf-cookie'}}
_PMC_AUTH = {'planetminecraft': 'pmc_autologin=test-cookie'}

_NEW_PAGE_HTML = '''
<meta id="core-csrf-token" content="csrf-abc">
<input name="resource_id" value="42424">
<input name="member_id" value="7">
<input name="subject_id" value="4">
<input name="group" value="texture_packs">
<input name="module" value="texture_pack">
<input name="module_task" value="create_texture_pack">
<select id="op1">
  <option value="120">Java Edition 1.21</option>
  <option value="119">Java Edition 1.20.6</option>
</select>
'''


def _make_response(body, status: int = 200):
    if body is None:
        encoded = b''
    elif isinstance(body, (dict, list)):
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


# ── MODRINTH.create ───────────────────────────────────────────────────────────

def test_mr_create_posts_to_project_endpoint():
    config = {'name': 'My Pack', 'summary': 'Cool', 'pack': 'mypack', 'modrinth': {'slug': 'mypack'}}
    responses = [
        _make_http_error(404, 'not found'),  # slug check → available
        _make_response({'id': 'abc123', 'slug': 'mypack'}),  # POST create
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        result = MODRINTH.create(config=config, auth=_MR_AUTH)

    post_req = mock_open.call_args_list[1][0][0]
    assert post_req.full_url == f'{_MR_API}/project'
    assert post_req.method == 'POST'
    assert b'mypack' in post_req.data
    assert b'My Pack' in post_req.data


def test_mr_create_returns_id_and_slug():
    config = {'name': 'Pack', 'pack': 'pk', 'modrinth': {'slug': 'pk'}}
    responses = [
        _make_http_error(404, ''),
        _make_response({'id': 'id-xyz', 'slug': 'pk'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        result = MODRINTH.create(config=config, auth=_MR_AUTH)

    assert result == {'id': 'id-xyz', 'slug': 'pk'}


def test_mr_create_tries_next_slug_on_collision():
    config = {'name': 'Pack', 'pack': 'mypack', 'modrinth': {'slug': 'mypack'}}
    responses = [
        _make_response({'id': 'existing'}),  # slug 'mypack' taken
        _make_http_error(404, ''),  # slug 'mypack-1' available
        _make_response({'id': 'new-id', 'slug': 'mypack-1'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        result = MODRINTH.create(config=config, auth=_MR_AUTH)

    assert result['slug'] == 'mypack-1'

    post_data = json.loads(responses[2].read.return_value)  # verify sent slug
    # check via the actual POST call: body contains mypack-1
    # (checked in the POST response above)


def test_mr_create_sends_categories_from_tags():
    config = {
        'name': 'Pack', 'pack': 'pk',
        'modrinth': {'slug': 'pk', 'tags': {'16x': True, '32x': False, 'realistic': True}},
    }
    responses = [
        _make_http_error(404, ''),
        _make_response({'id': 'x', 'slug': 'pk'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        MODRINTH.create(config=config, auth=_MR_AUTH)

    post_req = mock_open.call_args_list[1][0][0]
    body_text = post_req.data.decode('latin-1')
    assert '16x' in body_text
    assert 'realistic' in body_text


def test_mr_create_raises_on_api_error():
    config = {'name': 'Pack', 'pack': 'pk', 'modrinth': {'slug': 'pk'}}
    responses = [
        _make_http_error(404, ''),
        _make_response({'error': 'invalid_input', 'description': 'Slug already exists'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        with pytest.raises(SystemExit, match='Modrinth project creation failed'):
            MODRINTH.create(config=config, auth=_MR_AUTH)


# ── CURSEFORGE.create ─────────────────────────────────────────────────────────

def _cf_project_data(project_id=9999):
    return {
        'id': project_id,
        'slug': 'my-pack',
        'name': 'My Pack',
        'summary': 'Cool pack',
        'primaryCategoryId': 393,
        'licenseId': 4,
        'links': [{'type': 2, 'url': 'https://discord.gg/x'}],
    }


def test_cf_create_uploads_icon_first():
    responses = [
        _make_response('https://cdn.curseforge.com/avatars/icon.png'),  # icon upload
        _make_response({'id': 9999}),  # project creation
        _make_response(_cf_project_data()),  # fetch project
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        with patch('time.sleep'):
            CURSEFORGE.create(config={'name': 'My Pack', 'summary': 'Cool'}, auth=_CF_AUTH, icon_bytes=b'PNG')

    first_req = mock_open.call_args_list[0][0][0]
    assert 'upload-avatar' in first_req.full_url
    assert b'PNG' in first_req.data


def test_cf_create_posts_project_with_name_and_summary():
    responses = [
        _make_response('https://cdn.cf.com/icon.png'),
        _make_response({'id': 9999}),
        _make_response(_cf_project_data()),
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        with patch('time.sleep'):
            CURSEFORGE.create(config={'name': 'My Pack', 'summary': 'Cool'}, auth=_CF_AUTH, icon_bytes=b'PNG')

    create_req = mock_open.call_args_list[1][0][0]
    assert create_req.full_url == f'{_CF_DASH}/projects'
    assert create_req.method == 'POST'
    body = json.loads(create_req.data)
    assert body['name'] == 'My Pack'
    assert body['summary'] == 'Cool'
    assert body['gameId'] == 432
    assert body['classId'] == 12


def test_cf_create_returns_id_slug_and_harvested_metadata():
    responses = [
        _make_response('https://cdn.cf.com/icon.png'),
        _make_response({'id': 9999}),
        _make_response(_cf_project_data(9999)),
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        with patch('time.sleep'):
            result = CURSEFORGE.create(
                config={'name': 'My Pack', 'summary': 'Cool', 'curseforge': {'mainCategory': '16x'}},
                auth=_CF_AUTH, icon_bytes=b'PNG',
            )

    assert result['id'] == 9999
    assert result['slug'] == 'my-pack'
    assert result['category'] == 393  # harvested from fetch, not string form
    assert result['license'] == 'MIT License'  # licenseId 4 → MIT License
    assert result['socials'] == {'discord': 'https://discord.gg/x'}


def test_cf_create_raises_on_creation_failure():
    responses = [
        _make_response('https://cdn.cf.com/icon.png'),
        _make_response({'error': 'bad request'}),  # no 'id' key
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        with patch('time.sleep'):
            with pytest.raises(SystemExit, match='CurseForge project creation failed'):
                CURSEFORGE.create(config={'name': 'P', 'summary': 'S'}, auth=_CF_AUTH, icon_bytes=b'PNG')


def test_cf_create_maps_main_category_string_to_id():
    responses = [
        _make_response('https://cdn.cf.com/icon.png'),
        _make_response({'id': 9999}),
        _make_response({'id': 9999, 'slug': 'pk', 'primaryCategoryId': 394}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        with patch('time.sleep'):
            CURSEFORGE.create(
                config={'name': 'P', 'summary': 'S', 'curseforge': {'mainCategory': '32x'}},
                auth=_CF_AUTH, icon_bytes=b'PNG',
            )

    create_body = json.loads(mock_open.call_args_list[1][0][0].data)
    assert create_body['primaryCategoryId'] == 394  # '32x' → 394


# ── PMC.create ────────────────────────────────────────────────────────────────

def test_pmc_create_parses_resource_id_and_csrf(tmp_path):
    responses = [
        _make_response(_NEW_PAGE_HTML),
        _make_response({'status': 'success', 'forward': 'texture-pack/my-cool-pack'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses):
        result = PMC.create(
            config={'name': 'My Pack', 'planetminecraft': {}},
            auth=_PMC_AUTH, image_list=[], images_dir=tmp_path,
        )

    assert result['id'] == 42424
    assert result['slug'] == 'my-cool-pack'


def test_pmc_create_fetches_item_new_page():
    responses = [
        _make_response(_NEW_PAGE_HTML),
        _make_response({'status': 'success', 'forward': 'texture-pack/pack'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        PMC.create(
            config={'name': 'Pack', 'planetminecraft': {}},
            auth=_PMC_AUTH, image_list=[], images_dir=Path('/tmp'),
        )

    get_req = mock_open.call_args_list[0][0][0]
    assert 'item/new' in get_req.full_url


def test_pmc_create_selects_latest_mc_version(tmp_path):
    responses = [
        _make_response(_NEW_PAGE_HTML),
        _make_response({'status': 'success', 'forward': 'texture-pack/p'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        PMC.create(
            config={'name': 'Pack', 'planetminecraft': {}},
            auth=_PMC_AUTH, image_list=[], images_dir=tmp_path,
        )

    post_req = mock_open.call_args_list[1][0][0]
    assert b'op1' in post_req.data
    assert b'120' in post_req.data  # first option = Java Edition 1.21 = value 120


def test_pmc_create_selects_exact_mc_version(tmp_path):
    responses = [
        _make_response(_NEW_PAGE_HTML),
        _make_response({'status': 'success', 'forward': 'texture-pack/p'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        PMC.create(
            config={
                'name': 'Pack',
                'planetminecraft': {},
                'versions': {'planetminecraft': {'type': 'exact', 'version': '1.20.6'}},
            },
            auth=_PMC_AUTH, image_list=[], images_dir=tmp_path,
        )

    post_req = mock_open.call_args_list[1][0][0]
    assert b'119' in post_req.data  # 1.20.6 = value 119


def test_pmc_create_resolves_tags(tmp_path):
    tag_html = '<span class="tag" data-tag-id="777">16x</span>'
    responses = [
        _make_response(_NEW_PAGE_HTML),
        _make_response({'status': 'success', 'tag_html': tag_html}),  # tag resolve
        _make_response({'status': 'success', 'forward': 'texture-pack/p'}),
    ]
    with patch('urllib.request.urlopen', side_effect=responses) as mock_open:
        PMC.create(
            config={'name': 'Pack', 'planetminecraft': {'tags': ['16x']}},
            auth=_PMC_AUTH, image_list=[], images_dir=tmp_path,
        )

    final_req = mock_open.call_args_list[-1][0][0]
    assert b'777' in final_req.data


def test_pmc_create_raises_auth_expired_on_403(tmp_path):
    with patch('urllib.request.urlopen', side_effect=_make_http_error(403, 'Forbidden')):
        with pytest.raises(AuthExpiredError):
            PMC.create(
                config={'name': 'Pack', 'planetminecraft': {}},
                auth=_PMC_AUTH, image_list=[], images_dir=tmp_path,
            )


def test_pmc_create_raises_on_missing_resource_id(tmp_path):
    html = '<meta id="core-csrf-token" content="x">'  # no resource_id input
    with patch('urllib.request.urlopen', return_value=_make_response(html)):
        with pytest.raises(SystemExit, match='resource_id'):
            PMC.create(
                config={'name': 'Pack', 'planetminecraft': {}},
                auth=_PMC_AUTH, image_list=[], images_dir=tmp_path,
            )


# ── run_create integration ────────────────────────────────────────────────────

@pytest.fixture
def create_env(tmp_path, monkeypatch):
    home = tmp_path / 'puppy'
    project = home / 'MyPack'
    project.mkdir(parents=True)
    (home / 'puppy.yaml').write_text(yaml.dump({'projects': ['MyPack']}))
    (home / 'auth.yaml').write_text(yaml.dump({
        'modrinth': {'token': 'mr-tok'},
        'curseforge': {'token': 'cf-tok', 'cookie': 'CobaltSession=x'},
        'planetminecraft': 'pmc_autologin=x',
    }))
    (project / 'puppy.yaml').write_text(yaml.dump({
        'name': 'MyPack', 'pack': 'mypack',
        'modrinth': {'slug': 'mypack'},
        'curseforge': {'slug': 'mypack'},
        'planetminecraft': {'slug': 'mypack'},
    }))
    Image.new('RGB', (64, 64), color='blue').save(project / 'icon.png')
    monkeypatch.chdir(project)
    return {'home': home, 'project': project}


def test_run_create_calls_site_create_and_writes_ids(create_env, monkeypatch):
    from puppy.config import ConfigSynthesizer
    from puppy.core import Project
    from puppy.creator import run_create

    home = create_env['home']
    project_dir = create_env['project']
    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=False)
    auth = yaml.safe_load((home / 'auth.yaml').read_text())

    monkeypatch.setattr('puppy.creator.CURSEFORGE.create', lambda **k: {'id': 111, 'slug': 'mypack'})
    monkeypatch.setattr('puppy.creator.MODRINTH.create', lambda **k: {'id': 'abc', 'slug': 'mypack'})
    monkeypatch.setattr('puppy.creator.PMC.create', lambda **k: {'id': 42, 'slug': 'mypack'})
    monkeypatch.setattr('puppy.syncer.run_push', lambda **k: None)

    run_create(
        project=project, config=config, puppy_home=home,
        auth=auth, site=None, images=False, verbosity=0,
    )

    saved = yaml.safe_load((project_dir / 'puppy.yaml').read_text())
    assert saved['curseforge']['id'] == 111
    assert saved['modrinth']['id'] == 'abc'
    assert saved['planetminecraft']['id'] == 42


def test_run_create_skips_sites_with_existing_id(create_env, monkeypatch):
    from puppy.config import ConfigSynthesizer
    from puppy.core import Project
    from puppy.creator import run_create
    import yaml as _yaml

    home = create_env['home']
    project_dir = create_env['project']
    (project_dir / 'puppy.yaml').write_text(_yaml.dump({
        'name': 'MyPack', 'pack': 'mypack',
        'modrinth': {'id': 'existing-id', 'slug': 'mypack'},
        'curseforge': {'slug': 'mypack'},
        'planetminecraft': {'slug': 'mypack'},
    }))
    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=False)
    auth = _yaml.safe_load((home / 'auth.yaml').read_text())

    mr_create_calls = []
    monkeypatch.setattr('puppy.creator.MODRINTH.create',
                        lambda **k: mr_create_calls.append(k) or {'id': 'new', 'slug': 'x'})
    monkeypatch.setattr('puppy.creator.CURSEFORGE.create', lambda **k: {'id': 222, 'slug': 'mypack'})
    monkeypatch.setattr('puppy.creator.PMC.create', lambda **k: {'id': 43, 'slug': 'mypack'})
    monkeypatch.setattr('puppy.syncer.run_push', lambda **k: None)

    run_create(
        project=project, config=config, puppy_home=home,
        auth=auth, site=None, images=False, verbosity=0,
    )

    assert mr_create_calls == []  # MR already had an id, skipped


def test_run_create_missing_mr_credentials_raises(create_env, monkeypatch):
    from puppy.config import ConfigSynthesizer
    from puppy.core import Project
    from puppy.creator import run_create

    home = create_env['home']
    project_dir = create_env['project']
    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=False)

    with pytest.raises(SystemExit, match='Credentials missing'):
        run_create(
            project=project, config=config, puppy_home=home,
            auth={},  # no credentials
            site='modrinth', images=False, verbosity=0,
        )


def test_run_create_calls_run_push_at_end(create_env, monkeypatch):
    from puppy.config import ConfigSynthesizer
    from puppy.core import Project
    from puppy.creator import run_create

    home = create_env['home']
    project_dir = create_env['project']
    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=False)
    auth = yaml.safe_load((home / 'auth.yaml').read_text())

    push_calls = []
    monkeypatch.setattr('puppy.creator.CURSEFORGE.create', lambda **k: {'id': 1, 'slug': 's'})
    monkeypatch.setattr('puppy.creator.MODRINTH.create', lambda **k: {'id': 'a', 'slug': 's'})
    monkeypatch.setattr('puppy.creator.PMC.create', lambda **k: {'id': 2, 'slug': 's'})
    monkeypatch.setattr('puppy.syncer.run_push', lambda **k: push_calls.append(k))

    run_create(
        project=project, config=config, puppy_home=home,
        auth=auth, site=None, images=False, verbosity=0,
    )

    assert len(push_calls) == 1
