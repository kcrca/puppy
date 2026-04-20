import json
import subprocess
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from puppy.core import Project
from puppy.creator import _stage, run_create


@pytest.fixture
def worker_dir(tmp_path):
    d = tmp_path / "worker"
    d.mkdir()
    return d


@pytest.fixture
def project_setup(tmp_path):
    project_root = tmp_path / "MyPack"
    puppy_dir = project_root / "puppy"
    puppy_dir.mkdir(parents=True)

    icon = puppy_dir / "icon.png"
    Image.new("RGB", (64, 64), color="blue").save(icon)

    zip_path = puppy_dir / "mypack.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("pack.mcmeta", '{}')

    config = {
        "name": "MyPack",
        "pack": "mypack",
        "summary": "A test pack",
        "curseforge": {"id": 111, "slug": "mypack"},
        "modrinth": {"id": "abc123", "slug": "mypack"},
        "planetminecraft": {"id": 999, "slug": "mypack"},
    }
    project = Project(project_root, override_name="MyPack", override_pack="mypack")
    return project, config, puppy_dir, icon, zip_path


def test_create_json_fields(project_setup, worker_dir):
    project, config, puppy_dir, icon, zip_path = project_setup
    _stage(project, config, icon, zip_path, puppy_dir, worker_dir, site=None)

    data = json.loads((worker_dir / "data" / "create" / "create.json").read_text())
    assert data["id"] == "mypack"
    assert data["name"] == "MyPack"
    assert data["summary"] == "A test pack"


def test_create_icon_and_zip_staged(project_setup, worker_dir):
    project, config, puppy_dir, icon, zip_path = project_setup
    _stage(project, config, icon, zip_path, puppy_dir, worker_dir, site=None)

    assert (worker_dir / "data" / "create" / "pack.png").exists()
    assert (worker_dir / "data" / "create" / "pack.zip").exists()


def test_create_project_json_staged(project_setup, worker_dir):
    project, config, puppy_dir, icon, zip_path = project_setup
    _stage(project, config, icon, zip_path, puppy_dir, worker_dir, site=None)

    pj = json.loads((worker_dir / "projects" / "mypack" / "project.json").read_text())
    assert pj["curseforge"]["id"] == 111
    assert pj["modrinth"]["id"] == "abc123"
    assert pj["planetminecraft"]["id"] == 999


def test_create_site_filter_nulls_others(project_setup, worker_dir):
    project, config, puppy_dir, icon, zip_path = project_setup
    _stage(project, config, icon, zip_path, puppy_dir, worker_dir, site="modrinth")

    pj = json.loads((worker_dir / "projects" / "mypack" / "project.json").read_text())
    assert pj["modrinth"]["id"] == "abc123"
    assert pj["curseforge"]["id"] is None
    assert pj["planetminecraft"]["id"] is None


def test_create_webp_icon_converted(project_setup, worker_dir):
    project, config, puppy_dir, icon, zip_path = project_setup
    webp = puppy_dir / "icon.webp"
    Image.new("RGB", (64, 64), color="red").save(webp)
    config = dict(config, icon="icon.webp")

    _stage(project, config, webp, zip_path, puppy_dir, worker_dir, site=None)

    staged = worker_dir / "data" / "create" / "pack.png"
    assert staged.exists()
    with Image.open(staged) as img:
        assert img.format == "PNG"


def test_run_create_calls_worker(project_setup, worker_dir, monkeypatch):
    project, config, puppy_dir, icon, zip_path = project_setup
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("puppy.creator._read_output", lambda p, w: {
        "curseforge": {"id": 111, "slug": "mypack"},
        "modrinth": {"id": "abc123", "slug": "mypack"},
        "planetminecraft": {"id": 999, "slug": "mypack"},
    })

    run_create(project=project, config=config, worker_dir=worker_dir, site=None, verbosity=0)
    assert any("create.js" in " ".join(c) for c in calls)
