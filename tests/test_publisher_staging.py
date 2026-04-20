import json
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml
from PIL import Image

from puppy.core import Project
from puppy.publisher import _stage, _patch_project_json, _save_pmc_version, _pmc_needs_upload


@pytest.fixture
def project_setup(tmp_path):
    project_root = tmp_path / "MyPack"
    puppy_dir = project_root / "puppy"
    puppy_dir.mkdir(parents=True)

    zip_path = puppy_dir / "mypack-1.0.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("pack.mcmeta", '{}')

    config = {
        "name": "MyPack",
        "pack": "mypack",
        "minecraft": "1.20",
        "curseforge": {"id": 111, "slug": "mypack"},
        "modrinth": {"id": "abc123", "slug": "mypack"},
        "planetminecraft": {"id": 999, "slug": "mypack"},
    }
    project = Project(project_root, override_name="MyPack", override_pack="mypack")
    return project, config, puppy_dir, zip_path


@pytest.fixture
def worker_dir(tmp_path):
    d = tmp_path / "worker"
    d.mkdir()
    # pre-stage a project.json as syncer would have done
    project_dir = d / "projects" / "mypack"
    project_dir.mkdir(parents=True)
    from puppy.creator import _build_config
    cfg = {"id": "mypack", "name": "MyPack", "summary": "", "description": [],
           "optifine": False, "video": False, "github": False,
           "version": "1.0.0", "versions": {}, "images": [],
           "curseforge": {}, "modrinth": {}, "planetminecraft": {}}
    (project_dir / "project.json").write_text(json.dumps({
        "config": cfg,
        "curseforge": {"id": 111, "slug": "mypack"},
        "modrinth": {"id": "abc123", "slug": "mypack"},
        "planetminecraft": {"id": 999, "slug": "mypack"},
    }))
    return d


def test_update_json_staged(project_setup, worker_dir):
    project, config, puppy_dir, zip_path = project_setup
    _stage(project, config, zip_path, worker_dir, version="1.0.0")

    data = json.loads((worker_dir / "data" / "update" / "update.json").read_text())
    assert data["id"] == "mypack"
    assert data["version"] == "1.0.0"
    assert (worker_dir / "data" / "update" / "pack.zip").exists()


def test_patch_project_json_nulls_skipped_sites(project_setup, worker_dir):
    project, config, puppy_dir, zip_path = project_setup
    _patch_project_json(worker_dir, project, config, sites_to_upload=["modrinth"])

    pj = json.loads((worker_dir / "projects" / "mypack" / "project.json").read_text())
    assert pj["modrinth"]["id"] == "abc123"
    assert pj["curseforge"]["id"] is None
    assert pj["planetminecraft"]["id"] is None


def test_patch_project_json_all_sites(project_setup, worker_dir):
    project, config, puppy_dir, zip_path = project_setup
    _patch_project_json(worker_dir, project, config, sites_to_upload=["curseforge", "modrinth", "planetminecraft"])

    pj = json.loads((worker_dir / "projects" / "mypack" / "project.json").read_text())
    assert pj["curseforge"]["id"] == 111
    assert pj["modrinth"]["id"] == "abc123"
    assert pj["planetminecraft"]["id"] == 999


def test_save_and_check_pmc_version(project_setup):
    project, config, puppy_dir, zip_path = project_setup
    assert _pmc_needs_upload(project, "1.0.0") is True

    _save_pmc_version(puppy_dir, "1.0.0")
    assert _pmc_needs_upload(project, "1.0.0") is False
    assert _pmc_needs_upload(project, "1.0.1") is True
