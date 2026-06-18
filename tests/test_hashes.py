import yaml
import pytest
from PIL import Image

from puppy import hashes
from puppy import syncer
from puppy.config import ConfigSynthesizer
from puppy.core import Project
from puppy.syncer import run_push
from puppy.syncer import _push_images as _REAL_PUSH_IMAGES  # captured before conftest stubs it


# ── image hash folds in the encoding recipe ───────────────────────────────────

def test_image_hash_changes_with_encoding(tmp_path, monkeypatch):
    img = tmp_path / 'shot.png'
    Image.new('RGB', (10, 10)).save(img)
    entry = {'file': 'shot', 'name': 'Shot'}
    h1 = syncer._image_hash(img, entry)
    monkeypatch.setattr('puppy.syncer.GALLERY_ENCODING', 'jpeg:1x1:q1')
    assert syncer._image_hash(img, entry) != h1


def test_icon_hash_changes_with_encoding(tmp_path, monkeypatch):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (16, 16)).save(icon)
    h1 = syncer._icon_hash(icon)
    monkeypatch.setattr('puppy.syncer.ICON_ENCODING', 'png:1x1')
    assert syncer._icon_hash(icon) != h1


def test_push_images_warns_when_icon_removed(capsys):
    class _Stub:
        label = 'TestSite'

        def gallery_urls(self, *a, **k):
            return {}

    store = {'images': {'@icon': 'oldhash'}}
    urls, avatar = _REAL_PUSH_IMAGES(
        _Stub(), 'pid', {}, [], None, None,
        set(), True, store, 'pack', 0,
    )
    assert 'icon removed' in capsys.readouterr().out
    assert avatar is None
    assert '@icon' not in store['images']   # tracked hash dropped, no upload


# ── parse_content ──────────────────────────────────────────────────────────────

def test_parse_content_letters():
    assert hashes.parse_content('fid') == {'file', 'images', 'data'}


def test_parse_content_words():
    assert hashes.parse_content('file,data') == {'file', 'data'}


def test_parse_content_single_word():
    assert hashes.parse_content('images') == {'images'}


def test_parse_content_all():
    assert hashes.parse_content('all') == {'file', 'images', 'data'}


def test_parse_content_unknown_raises():
    with pytest.raises(SystemExit, match='unknown content category'):
        hashes.parse_content('x')


# ── decide ────────────────────────────────────────────────────────────────────

def test_decide_no_hashes_only_named():
    assert hashes.decide('data', 'h', upload_set={'data'}, use_hashes=False, prior={}) is True
    assert hashes.decide('images', 'h', upload_set={'data'}, use_hashes=False, prior={}) is False


def test_decide_hashes_forced_ignores_match():
    assert hashes.decide('data', 'h', upload_set={'data'}, use_hashes=True, prior={'data': 'h'}) is True


def test_decide_hashes_skip_when_match():
    assert hashes.decide('data', 'h', upload_set=set(), use_hashes=True, prior={'data': 'h'}) is False


def test_decide_hashes_upload_when_changed():
    assert hashes.decide('data', 'h2', upload_set=set(), use_hashes=True, prior={'data': 'h1'}) is True


# ── run_push hashing behavior ─────────────────────────────────────────────────

def _env(tmp_path, extra=None):
    home = tmp_path / 'neon' / 'puppy'
    project_dir = home / 'MyPack'
    project_dir.mkdir(parents=True)
    (home / '.gitignore').write_text('auth.yaml\n')
    (home / 'puppy.yaml').write_text(yaml.dump({'projects': ['MyPack']}))
    (home / 'auth.yaml').write_text(yaml.dump({
        'curseforge': {'token': 'cf', 'cookie': 'CobaltSession=x'},
    }))
    cfg = {
        'name': 'MyPack', 'handle': 'mypack', 'type': 'pack',
        'curseforge': {'id': 99, 'slug': 'mypack'},
    }
    if extra:
        cfg.update(extra)
    (project_dir / 'puppy.yaml').write_text(yaml.dump(cfg))
    Image.new('RGB', (64, 64), color='blue').save(project_dir / 'icon.png')
    return home, project_dir


def _run(home, project_dir, **kw):
    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=True)
    auth = {'curseforge': {'token': 'cf', 'cookie': 'CobaltSession=x'}}
    run_push(project=project, config=config, puppy_home=home, site='curseforge',
             version=None, verbosity=0, auth=auth, **kw)


def test_data_uploads_then_skips_when_unchanged(tmp_path, monkeypatch):
    home, project_dir = _env(tmp_path)
    calls = []
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: calls.append(1))
    _run(home, project_dir, content=set())
    _run(home, project_dir, content=set())
    assert calls == [1]                       # second run skipped
    assert (project_dir / 'hashes.yaml').exists()


def test_force_data_reuploads_even_when_unchanged(tmp_path, monkeypatch):
    home, project_dir = _env(tmp_path)
    calls = []
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: calls.append(1))
    _run(home, project_dir, content=set())
    _run(home, project_dir, content={'data'})  # forced
    assert calls == [1, 1]


def test_rehash_records_without_uploading_then_push_skips(tmp_path, monkeypatch):
    home, project_dir = _env(tmp_path)
    calls = []
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: calls.append(1))
    _run(home, project_dir, rehash=True)
    assert calls == []                          # rehash uploads nothing
    assert (project_dir / 'hashes.yaml').exists()
    _run(home, project_dir, content=set())      # push sees data already recorded
    assert calls == []


def test_rehash_scope_images_only(tmp_path, monkeypatch):
    home, project_dir = _env(tmp_path)
    calls = []
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: calls.append(1))
    _run(home, project_dir, rehash=True, content={'images'})
    store = yaml.safe_load((project_dir / 'hashes.yaml').read_text())
    assert 'images' in store['curseforge']
    assert 'data' not in store['curseforge']
    _run(home, project_dir, content=set())      # data was not recorded → still uploads
    assert calls == [1]


def test_rehash_records_file_then_push_skips(tmp_path, monkeypatch):
    import zipfile
    home, project_dir = _env(tmp_path, extra={'minecraft': '1.21', 'file': 'pack.zip'})
    with zipfile.ZipFile(project_dir / 'pack.zip', 'w') as z:
        z.writestr('pack.mcmeta', '{}')
    uploads = []
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: None)
    monkeypatch.setattr('puppy.syncer._upload_site', lambda *a, **k: uploads.append(1))

    config = ConfigSynthesizer(home, project_dir).get_running_config()
    project = Project.from_config(project_dir, config, dry_run=True)
    auth = {'curseforge': {'token': 'cf', 'cookie': 'CobaltSession=x'}}
    run_push(project=project, config=config, puppy_home=home, site='curseforge',
             version='1.0.0', verbosity=0, auth=auth, rehash=True)
    assert uploads == []                        # rehash uploads no file
    store = yaml.safe_load((project_dir / 'hashes.yaml').read_text())
    assert 'file' in store['curseforge']

    run_push(project=project, config=config, puppy_home=home, site='curseforge',
             version='1.0.0', verbosity=0, auth=auth, content=set())
    assert uploads == []                        # zip unchanged → still skipped


def test_use_hashes_false_only_uploads_named(tmp_path, monkeypatch):
    home, project_dir = _env(tmp_path, extra={'use_hashes': False})
    calls = []
    monkeypatch.setattr('puppy.syncer._run_site', lambda *a, **k: calls.append(1))
    _run(home, project_dir, content={'data'})
    assert calls == [1]
    _run(home, project_dir, content=set())     # data not named → nothing
    assert calls == [1]
    assert not (project_dir / 'hashes.yaml').exists()
