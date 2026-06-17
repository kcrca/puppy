import yaml
import pytest
from PIL import Image

from puppy import hashes
from puppy.config import ConfigSynthesizer
from puppy.core import Project
from puppy.syncer import run_push


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
    monkeypatch.setattr('puppy.syncer._run_cf', lambda *a, **k: calls.append(1))
    _run(home, project_dir, content=set())
    _run(home, project_dir, content=set())
    assert calls == [1]                       # second run skipped
    assert (project_dir / 'hashes.yaml').exists()


def test_force_data_reuploads_even_when_unchanged(tmp_path, monkeypatch):
    home, project_dir = _env(tmp_path)
    calls = []
    monkeypatch.setattr('puppy.syncer._run_cf', lambda *a, **k: calls.append(1))
    _run(home, project_dir, content=set())
    _run(home, project_dir, content={'data'})  # forced
    assert calls == [1, 1]


def test_use_hashes_false_only_uploads_named(tmp_path, monkeypatch):
    home, project_dir = _env(tmp_path, extra={'use_hashes': False})
    calls = []
    monkeypatch.setattr('puppy.syncer._run_cf', lambda *a, **k: calls.append(1))
    _run(home, project_dir, content={'data'})
    assert calls == [1]
    _run(home, project_dir, content=set())     # data not named → nothing
    assert calls == [1]
    assert not (project_dir / 'hashes.yaml').exists()
