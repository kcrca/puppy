import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

import yaml

from puppy.core import Project
from puppy.sites import SITES, SiteVisitor


def run_import(*, project: Project, config: dict, auth: dict, worker_dir: Path, site: str | None, verbosity: int) -> None:
    config = _resolve_ids(config, auth, site, verbosity)
    _stage(project, config, worker_dir, site)
    _clean_existing(project, worker_dir)
    _run_worker(worker_dir, verbosity)
    result_data = _read_output(project, worker_dir)
    _harvest(project, result_data, worker_dir, site)
    if verbosity >= 1:
        print(f"[{project.name}] import complete")


def _resolve_ids(config: dict, auth: dict, site: str | None, verbosity: int) -> dict:
    config = dict(config)

    modrinth = config.get("modrinth", {})
    if (not site or site == "modrinth") and not modrinth.get("id") and modrinth.get("slug"):
        slug = modrinth["slug"]
        try:
            headers = {"User-Agent": "puppy/1.0"}
            token = auth.get("modrinth")
            if token:
                headers["Authorization"] = token
            req = urllib.request.Request(
                f"https://api.modrinth.com/v2/project/{slug}",
                headers=headers,
            )
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
            config["modrinth"] = dict(modrinth, id=data["id"], slug=data["slug"])
            if verbosity >= 1:
                print(f"Resolved Modrinth ID for slug '{slug}': {data['id']}")
        except Exception as e:
            raise SystemExit(f"Could not resolve Modrinth ID for slug '{slug}': {e}")

    return config


def _stage(project: Project, config: dict, worker_dir: Path, site: str | None) -> None:
    import_data: dict = {"id": project.pack}
    visitor = SiteVisitor(site)
    for s in SITES:
        site_cfg = config.get(s, {})
        import_data[s] = {
            "id": visitor.id_or_skip(s, site_cfg.get("id")),
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
        images = [
            {**img, "file": img["file"].strip("_")} if "file" in img else img
            for img in imported["images"]
        ]
        if (puppy_dir / "images.yaml").exists():
            images_yaml = puppy_dir / "images.yaml"
        else:
            images_yaml = puppy_dir / "images" / "images.yaml"
            images_yaml.parent.mkdir(parents=True, exist_ok=True)
        with images_yaml.open("w") as f:
            yaml.dump(images, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        config.pop("images", None)

    # Platform IDs/slugs and site-specific config
    for s in SiteVisitor(site):
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
    dest.mkdir(parents=True, exist_ok=True)
    for p in dest.iterdir():
        if p.suffix != ".yaml":
            p.unlink()
    for img in src.iterdir():
        clean_name = img.stem.strip("_") + img.suffix
        shutil.copy(img, dest / clean_name)

