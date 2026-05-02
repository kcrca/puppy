import json
import subprocess
import pytest
import yaml

from puppy.puller import _has_image_info

_PACK = 'neonglow'
_PROJECT_JSON = {
    'config': {
        'name': 'NeonGlow', 'summary': 'A pack', 'version': '1.0.0',
        'images': [{'file': 'shot1.png', 'name': 'Shot 1'}, {'file': 'shot2.png', 'name': 'Shot 2'}],
    },
    'curseforge': {'id': 111, 'slug': _PACK},
    'modrinth': {'id': 'abc123', 'slug': _PACK},
    'planetminecraft': {'id': 999, 'slug': _PACK},
}


@pytest.fixture(autouse=True)
def _fake_urlopen(monkeypatch):
    monkeypatch.setattr('puppy.runner._worker_prep', lambda *a, **k: None)
    monkeypatch.setattr('puppy.puller.urllib.request.urlopen', lambda req: _FakeResponse())


class _FakeResponse:
    def __init__(self):
        import json as _json
        self._data = _json.dumps({'body': '', 'data': '', 'slug': _PACK}).encode()

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def _write_project_json_with_icon(worker_dir):
    pd = worker_dir / 'projects' / _PACK
    pd.mkdir(parents=True, exist_ok=True)
    (pd / 'pack.png').write_bytes(b'fakepng')
    (pd / 'project.json').write_text(json.dumps(_PROJECT_JSON))


def _write_project_json_with_images(worker_dir, image_names):
    pd = worker_dir / 'projects' / _PACK
    pd.mkdir(parents=True, exist_ok=True)
    images_dir = pd / 'images'
    images_dir.mkdir()
    for name in image_names:
        (images_dir / name).write_bytes(b'fakepng')
    (pd / 'project.json').write_text(json.dumps(_PROJECT_JSON))


@pytest.fixture
def import_env(project_env, worker_env, monkeypatch):
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({
            'name': 'NeonGlow',
            'pack': _PACK,
            'curseforge': {'id': 111, 'slug': _PACK},
            'modrinth': {'id': 'abc123', 'slug': _PACK},
            'planetminecraft': {'id': 999, 'slug': _PACK},
        })
    )

    def fake_run(cmd, **kwargs):
        _write_project_json_with_images(worker_env, ['shot1.png', 'shot2.png'])
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr('puppy.worker.subprocess.run', fake_run)
    return {**project_env, 'worker': worker_env}


# --- Unit tests for _has_image_info ---

def test_has_image_info_empty(tmp_path):
    assert not _has_image_info(tmp_path, None)


def test_has_image_info_top_level_yaml(tmp_path):
    (tmp_path / 'images.yaml').write_text('[]')
    assert _has_image_info(tmp_path, None)


def test_has_image_info_nested_yaml(tmp_path):
    (tmp_path / 'images').mkdir()
    (tmp_path / 'images' / 'images.yaml').write_text('[]')
    assert _has_image_info(tmp_path, None)


def test_has_image_info_site_specific(tmp_path):
    (tmp_path / 'modrinth').mkdir()
    (tmp_path / 'modrinth' / 'images.yaml').write_text('[]')
    assert _has_image_info(tmp_path, 'modrinth')


def test_has_image_info_site_specific_not_checked_for_other_site(tmp_path):
    (tmp_path / 'modrinth').mkdir()
    (tmp_path / 'modrinth' / 'images.yaml').write_text('[]')
    assert not _has_image_info(tmp_path, 'curseforge')


def test_has_image_info_site_nested_yaml(tmp_path):
    (tmp_path / 'curseforge' / 'images').mkdir(parents=True)
    (tmp_path / 'curseforge' / 'images' / 'images.yaml').write_text('[]')
    assert _has_image_info(tmp_path, 'curseforge')


# --- Integration tests for auto-download behaviour ---

def test_images_downloaded_when_no_info(import_env, run_puppy):
    run_puppy('pull', '--worker', str(import_env['worker']))
    assert (import_env['project'] / 'images').exists()
    assert any((import_env['project'] / 'images').iterdir())


def test_images_not_downloaded_when_info_exists(import_env, run_puppy):
    (import_env['project'] / 'images.yaml').write_text('[]')
    run_puppy('pull', '--worker', str(import_env['worker']))
    assert not (import_env['project'] / 'images').exists()


def test_images_downloaded_when_info_exists_with_flag(import_env, run_puppy):
    (import_env['project'] / 'images.yaml').write_text('[]')
    run_puppy('pull', '--images', '--worker', str(import_env['worker']))
    assert (import_env['project'] / 'images').exists()
    assert any((import_env['project'] / 'images').iterdir())


def test_yaml_written_to_images_subdir(import_env, run_puppy):
    run_puppy('pull', '--worker', str(import_env['worker']))
    assert (import_env['project'] / 'images' / 'images.yaml').exists()
    assert not (import_env['project'] / 'images.yaml').exists()


def test_top_level_images_yaml_removed_when_images_downloaded(import_env, run_puppy):
    (import_env['project'] / 'images.yaml').write_text('[]')
    run_puppy('pull', '--images', '--worker', str(import_env['worker']))
    assert (import_env['project'] / 'images' / 'images.yaml').exists()
    assert not (import_env['project'] / 'images.yaml').exists()


@pytest.fixture
def icon_import_env(project_env, worker_env, monkeypatch):
    (project_env['project'] / 'puppy.yaml').write_text(
        yaml.dump({
            'name': 'NeonGlow', 'pack': _PACK,
            'curseforge': {'id': 111, 'slug': _PACK},
            'modrinth': {'id': 'abc123', 'slug': _PACK},
            'planetminecraft': {'id': 999, 'slug': _PACK},
        })
    )
    def fake_run(cmd, **kwargs):
        _write_project_json_with_icon(worker_env)
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr('puppy.worker.subprocess.run', fake_run)
    return {**project_env, 'worker': worker_env}


def test_icon_harvested_when_no_icon_exists(icon_import_env, run_puppy):
    run_puppy('pull', '--worker', str(icon_import_env['worker']))
    assert (icon_import_env['project'] / 'pack.png').exists()


def test_icon_not_harvested_when_icon_exists(icon_import_env, run_puppy):
    (icon_import_env['project'] / 'myicon.png').write_bytes(b'existing')
    run_puppy('pull', '--worker', str(icon_import_env['worker']))
    assert not (icon_import_env['project'] / 'pack.png').exists()


def test_icon_not_harvested_without_images_flag_when_info_exists(icon_import_env, run_puppy):
    (icon_import_env['project'] / 'images.yaml').write_text('[]')
    run_puppy('pull', '--worker', str(icon_import_env['worker']))
    assert not (icon_import_env['project'] / 'pack.png').exists()


def test_icon_harvested_with_images_flag(icon_import_env, run_puppy):
    (icon_import_env['project'] / 'images.yaml').write_text('[]')
    run_puppy('pull', '--images', '--worker', str(icon_import_env['worker']))
    assert (icon_import_env['project'] / 'pack.png').exists()
