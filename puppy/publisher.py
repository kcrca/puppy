import hashlib
import json
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from puppy.core import Project
from puppy.creator import SITES


def upload_pack(*, project: Project, config: dict, worker_dir: Path, site: str | None, version: str, force: bool, verbosity: int) -> None:
    if not config.get("minecraft") and not config.get("versions"):
        raise SystemExit(f"[{project.name}] push --pack requires 'minecraft:' or 'versions:' in puppy.yaml")
    puppy_dir = project.root / "puppy"
    zip_path = _resolve_zip(config, puppy_dir, version, project)
    auth = _read_auth(puppy_dir)

    sites_to_upload = _sites_needing_upload(project, config, auth, zip_path, version, site, force, verbosity)
    if not sites_to_upload:
        if verbosity >= 1:
            print(f"[{project.name}] pack already current on all sites, skipping upload")
        return

    _patch_project_json(worker_dir, project, config, sites_to_upload)
    _stage(project, config, zip_path, worker_dir, version)
    _run_worker(worker_dir, verbosity)

    if "planetminecraft" in sites_to_upload:
        _save_pmc_version(puppy_dir, version)


def _resolve_zip(config: dict, puppy_dir: Path, version: str, project: Project) -> Path:
    explicit = config.get("zip")
    if explicit:
        p = (puppy_dir / explicit).resolve()
        if not p.exists():
            raise SystemExit(f"Zip not found: {p}")
        return p
    from puppy.artifacts import ArtifactFinder
    try:
        return ArtifactFinder(puppy_dir).find(project=project.pack, version=version)
    except FileNotFoundError as e:
        raise SystemExit(str(e))


def _read_auth(puppy_dir: Path) -> dict:
    auth_path = puppy_dir / "auth.yaml"
    if not auth_path.exists():
        return {}
    return yaml.safe_load(auth_path.read_text()) or {}


def _sites_needing_upload(project: Project, config: dict, auth: dict, zip_path: Path, version: str, site: str | None, force: bool, verbosity: int) -> list[str]:
    candidates = [s for s in SITES if (not site or s == site) and config.get(s, {}).get("id")]
    result = []
    for s in candidates:
        if force:
            result.append(s)
            continue
        try:
            needed = _needs_upload(s, project, config, auth, zip_path, version)
        except Exception as e:
            if verbosity >= 1:
                print(f"WARNING: could not check {s} upload status ({e}), will upload")
            needed = True
        if needed:
            result.append(s)
        elif verbosity >= 1:
            print(f"[{project.name}] {s}: already current, skipping")
    return result


def _needs_upload(site: str, project: Project, config: dict, auth: dict, zip_path: Path, version: str) -> bool:
    site_id = config[site]["id"]
    if site == "modrinth":
        return _modrinth_needs_upload(site_id, auth.get("modrinth"), zip_path)
    if site == "curseforge":
        return _curseforge_needs_upload(site_id, auth.get("curseforge", {}), zip_path, version)
    if site == "planetminecraft":
        return _pmc_needs_upload(project, version)
    return True


def _modrinth_needs_upload(project_id: str, token: str | None, zip_path: Path) -> bool:
    local_hash = hashlib.sha512(zip_path.read_bytes()).hexdigest()
    headers = {"User-Agent": "puppy/1.0"}
    if token:
        headers["Authorization"] = token
    req = urllib.request.Request(
        f"https://api.modrinth.com/v2/project/{project_id}/version",
        headers=headers,
    )
    with urllib.request.urlopen(req) as r:
        versions = json.loads(r.read())
    for v in versions:
        for f in v.get("files", []):
            if f.get("hashes", {}).get("sha512") == local_hash:
                return False
    return True


def _curseforge_needs_upload(project_id: int, cf_auth: dict, zip_path: Path, version: str) -> bool:
    local_size = zip_path.stat().st_size
    params = urllib.parse.urlencode({
        "filter": json.dumps({"projectId": project_id}),
        "range": "[0, 0]",
        "sort": '["DateCreated", "DESC"]',
    })
    req = urllib.request.Request(
        f"https://authors.curseforge.com/_api/project-files?{params}",
        headers={"cookie": cf_auth.get("cookie", ""), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        files = json.loads(r.read())
    if not files:
        return True
    latest = files[0]
    return not (latest.get("size") == local_size and f"v{version}" in latest.get("displayName", ""))


def _pmc_needs_upload(project: Project, version: str) -> bool:
    state_path = project.root / "puppy" / ".publish_state.yaml"
    if not state_path.exists():
        return True
    state = yaml.safe_load(state_path.read_text()) or {}
    return state.get("planetminecraft", {}).get("version") != str(version)


def _save_pmc_version(puppy_dir: Path, version: str) -> None:
    state_path = puppy_dir / ".publish_state.yaml"
    state = yaml.safe_load(state_path.read_text()) if state_path.exists() else {}
    state = state or {}
    state.setdefault("planetminecraft", {})["version"] = str(version)
    state_path.write_text(yaml.dump(state, default_flow_style=False))


def _patch_project_json(worker_dir: Path, project: Project, config: dict, sites_to_upload: list[str]) -> None:
    from puppy.creator import _expand_versions
    path = worker_dir / "projects" / project.pack / "project.json"
    data = json.loads(path.read_text())
    data["config"]["version"] = None  # bypass update.js same-version check
    data["config"]["versions"] = _expand_versions(config)
    for s in SITES:
        if s not in sites_to_upload and s in data:
            data[s]["id"] = None
    path.write_text(json.dumps(data, indent=2))


def _stage(project: Project, config: dict, zip_path: Path, worker_dir: Path, version: str) -> None:
    from puppy.creator import _expand_versions
    update_dir = worker_dir / "data" / "update"
    if update_dir.exists():
        shutil.rmtree(update_dir)
    update_dir.mkdir(parents=True)
    update_json = {
        "id": project.pack,
        "version": version,
        "versions": _expand_versions(config),
    }
    (update_dir / "update.json").write_text(json.dumps(update_json, indent=2))
    shutil.copy(zip_path, update_dir / "pack.zip")


def _run_worker(worker_dir: Path, verbosity: int) -> None:
    cmd = ["node", "--no-warnings", "scripts/update.js"]
    kwargs: dict = {"cwd": worker_dir}
    if verbosity < 2:
        kwargs["capture_output"] = True
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        detail = result.stderr.decode() if verbosity < 2 else ""
        raise SystemExit(f"Worker upload failed\n{detail}".strip())
