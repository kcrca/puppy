import json
import shutil
import subprocess
from pathlib import Path

from puppy.core import Project
from puppy.creator import (
    SITES,
    _build_config,
    _find_icon,
    _resolve_asset,
    _validate_square,
)
from puppy.renderer import render
from puppy.searcher import ContentDiscovery

_TEMPLATE_EXT = {
    "curseforge": ".html",
    "modrinth": ".md",
    "planetminecraft": ".bbcode",
}

_SITE_NAMES = {
    "planetminecraft": "planetminecraft",
    "curseforge": "curseforge",
    "modrinth": "modrinth",
}


def run_push(*, project: Project, config: dict, worker_dir: Path, puppy_home: Path, site: str | None, version: str | None, pack: bool, force: bool, verbosity: int) -> None:
    puppy_dir = project.root / "puppy"
    icon = _resolve_asset(config.get("icon"), puppy_dir, _find_icon)
    _validate_square(icon)

    body, source = ContentDiscovery(puppy_home, project.root).find_description(site=site)
    if body:
        config = dict(config)
        config["description"] = [render(body, config, source=str(source))]

    _stage(project, config, icon, puppy_dir, worker_dir, site)
    _run_worker(worker_dir, verbosity)

    if pack:
        from puppy.publisher import upload_pack
        upload_pack(project=project, config=config, worker_dir=worker_dir, site=site, version=version, force=force, verbosity=verbosity)

    if verbosity >= 1:
        print(f"[{project.name}] push complete")


def _stage(
    project: Project,
    config: dict,
    icon: Path,
    puppy_dir: Path,
    worker_dir: Path,
    site: str | None,
) -> None:
    cfg = _build_config(project, config)

    # data/details.json
    data_dir = worker_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    details = {"id": project.pack, "images": True, "live": True}
    (data_dir / "details.json").write_text(json.dumps(details, indent=2))

    # projects/{pack}/
    project_dir = worker_dir / "projects" / project.pack
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True)

    platform_ids = {
        s: {
            "id": config.get(s, {}).get("id") if not site or s == site else None,
            "slug": config.get(s, {}).get("slug"),
        }
        for s in SITES
    }
    project_json = {"config": cfg, **platform_ids}
    (project_dir / "project.json").write_text(json.dumps(project_json, indent=2))

    from puppy.images import stage_image
    stage_image(icon, project_dir / "pack.png")

    _copy_images(config, puppy_dir, project_dir / "images")

    for optional in ("thumbnail.png", "logo.png"):
        src = puppy_dir / optional
        if src.exists():
            shutil.copy(src, project_dir / optional)

    _stage_templates(project_dir, puppy_dir, site)


_MINIMAL_TEMPLATE = {
    ".md": "{{ description }}\n\n{{ images }}\n",
    ".html": "{{ description }}\n\n{{ images }}\n",
    ".bbcode": "{{ description }}\n\n{{ images }}\n",
}


def _copy_images(config: dict, puppy_dir: Path, dest: Path) -> None:
    from puppy.images import find_image, stage_image
    src_dir = Path(config["images_source"]) if config.get("images_source") else puppy_dir / "images"
    for img in config.get("images", []):
        try:
            src = find_image(img["file"], src_dir)
            stage_image(src, dest / (Path(img["file"]).stem + ".png"))
        except SystemExit as e:
            print(f"WARNING: {e}")


def _stage_templates(project_dir: Path, puppy_dir: Path, site: str | None) -> None:
    templates_dir = project_dir / "templates"
    templates_dir.mkdir()
    for s, ext in _TEMPLATE_EXT.items():
        if site and s != site:
            continue
        dest = templates_dir / f"{s}{ext}"
        src = puppy_dir / s / f"description{ext}"
        if src.exists():
            shutil.copy(src, dest)
        else:
            dest.write_text(_MINIMAL_TEMPLATE[ext])


def _run_worker(worker_dir: Path, verbosity: int) -> None:
    cmd = ["node", "--no-warnings", "scripts/details.js"]
    kwargs: dict = {"cwd": worker_dir}
    if verbosity < 2:
        kwargs["capture_output"] = True
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        detail = result.stderr.decode() if verbosity < 2 else ""
        raise SystemExit(f"Worker sync failed\n{detail}".strip())
