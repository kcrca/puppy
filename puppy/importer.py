import json
import subprocess
import sys
from pathlib import Path

import yaml

from puppy.core import Project


SITES = ["curseforge", "modrinth", "planetminecraft"]


def run_import(*, project: Project, config: dict, worker_dir: Path, verbosity: int) -> None:
    _stage(project, config, worker_dir)
    _run_worker(worker_dir, verbosity)
    result_data = _read_output(project, worker_dir)
    _harvest(project, result_data)
    if verbosity >= 1:
        print(f"[{project.name}] import complete — IDs written to puppy.yaml")


def _stage(project: Project, config: dict, worker_dir: Path) -> None:
    import_data: dict = {"id": project.pack}
    for site in SITES:
        site_cfg = config.get(site, {})
        import_data[site] = {
            "id": site_cfg.get("id"),
            "slug": site_cfg.get("slug"),
        }
    data_dir = worker_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "import.json").write_text(json.dumps(import_data, indent=2))


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


def _harvest(project: Project, result_data: dict) -> None:
    puppy_yaml = project.root / "puppy" / "puppy.yaml"
    config = {}
    if puppy_yaml.exists():
        with puppy_yaml.open() as f:
            config = yaml.safe_load(f) or {}

    for site in SITES:
        if site in result_data:
            config.setdefault(site, {})
            config[site]["id"] = result_data[site].get("id")
            config[site]["slug"] = result_data[site].get("slug")

    puppy_yaml.parent.mkdir(parents=True, exist_ok=True)
    with puppy_yaml.open("w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
