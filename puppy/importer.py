import json
import shutil
import subprocess
from pathlib import Path

import yaml

from puppy.core import Project


SITES = ["curseforge", "modrinth", "planetminecraft"]

_TEMPLATE_EXT = {
    "curseforge": ".html",
    "modrinth": ".md",
    "planetminecraft": ".bbcode",
}


def run_import(*, project: Project, config: dict, worker_dir: Path, site: str | None, verbosity: int) -> None:
    _stage(project, config, worker_dir, site)
    _clean_existing(project, worker_dir)
    _run_worker(worker_dir, verbosity)
    result_data = _read_output(project, worker_dir)
    _harvest(project, result_data, worker_dir, site)
    if verbosity >= 1:
        print(f"[{project.name}] import complete")


def _stage(project: Project, config: dict, worker_dir: Path, site: str | None) -> None:
    import_data: dict = {"id": project.pack}
    for s in SITES:
        site_cfg = config.get(s, {})
        import_data[s] = {
            "id": site_cfg.get("id"),
            "slug": site_cfg.get("slug"),
        }
    data_dir = worker_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "import.json").write_text(json.dumps(import_data, indent=2))


def _clean_existing(project: Project, worker_dir: Path) -> None:
    existing = worker_dir / "projects" / project.pack
    if existing.exists():
        shutil.rmtree(existing)


def _run_worker(worker_dir: Path, verbosity: int) -> None:
    cmd = ["node", "--no-warnings", "scripts/import.js"]
    kwargs: dict = {"cwd": worker_dir}
    if verbosity < 2:
        kwargs["capture_output"] = True
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        detail = result.stderr.decode() if verbosity < 2 else ""
        raise SystemExit(f"Worker import failed\n{detail}".strip())


def _read_output(project: Project, worker_dir: Path) -> dict:
    project_json = worker_dir / "projects" / project.pack / "project.json"
    if not project_json.exists():
        raise SystemExit(
            f"[{project.name}] expected output not found: {project_json}\n"
            "Check that the platform IDs/slugs in puppy.yaml are correct."
        )
    with project_json.open() as f:
        return json.load(f)


def _harvest(project: Project, result_data: dict, worker_dir: Path, site: str | None) -> None:
    puppy_dir = project.root / "puppy"
    project_worker_dir = worker_dir / "projects" / project.pack

    _harvest_yaml(project, result_data, puppy_dir, site)
    _harvest_images(project_worker_dir, puppy_dir)
    _harvest_templates(project_worker_dir, puppy_dir, site)


def _harvest_yaml(project: Project, result_data: dict, puppy_dir: Path, site: str | None) -> None:
    puppy_yaml = puppy_dir / "puppy.yaml"
    config = {}
    if puppy_yaml.exists():
        with puppy_yaml.open() as f:
            config = yaml.safe_load(f) or {}

    imported = result_data.get("config", {})

    # Scalars from imported config
    for key in ("name", "summary", "version", "video", "github"):
        if imported.get(key) not in (None, "", [], False):
            config[key] = imported[key]

    if imported.get("images"):
        config["images"] = imported["images"]

    # Platform IDs/slugs and site-specific config
    for s in SITES:
        if site and s != site:
            continue
        if s in result_data:
            config.setdefault(s, {})
            config[s]["id"] = result_data[s].get("id")
            config[s]["slug"] = result_data[s].get("slug")
        if s in imported:
            config.setdefault(s, {}).update(imported[s])

    puppy_yaml.parent.mkdir(parents=True, exist_ok=True)
    with puppy_yaml.open("w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _harvest_images(project_worker_dir: Path, puppy_dir: Path) -> None:
    src = project_worker_dir / "images"
    if not src.exists():
        return
    dest = puppy_dir / "images"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _harvest_templates(project_worker_dir: Path, puppy_dir: Path, site: str | None) -> None:
    """
    Copy site description templates as starting points.
    Note: description body text is NOT imported — paste your content in manually.
    """
    src_templates = project_worker_dir / "templates"
    if not src_templates.exists():
        return
    for s, ext in _TEMPLATE_EXT.items():
        if site and s != site:
            continue
        src = src_templates / f"{s}{ext}"
        if not src.exists():
            continue
        dest_dir = puppy_dir / s
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"description{ext}"
        if dest.exists():
            print(f"WARNING: {dest} already exists — left untouched")
        else:
            shutil.copy(src, dest)
