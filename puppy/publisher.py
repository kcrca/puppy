import json
import shutil
import subprocess
from pathlib import Path

from puppy.artifacts import ArtifactFinder
from puppy.core import Project
from puppy.creator import _expand_versions
from puppy.sites import SITES, SiteVisitor


def upload_pack(
    *,
    project: Project,
    config: dict,
    worker_dir: Path,
    site: str | None,
    version: str,
    force: bool,
    verbosity: int,
) -> None:
    if not config.get('minecraft') and not config.get('versions'):
        raise SystemExit(
            f"[{project.name}] push --pack requires 'minecraft:' or 'versions:' in puppy.yaml"
        )
    puppy_dir = project.puppy_dir
    zip_path = _resolve_zip(config, puppy_dir, version, project)
    auth = _read_auth(puppy_dir)

    sites_to_upload = _sites_needing_upload(
        project, config, auth, zip_path, version, site, force, verbosity
    )
    if not sites_to_upload:
        if verbosity >= 1:
            print(
                f'[{project.name}] pack already current on all sites, skipping upload'
            )
        return

    _patch_project_json(worker_dir, project, config, sites_to_upload)
    _stage(project, config, zip_path, worker_dir, version)
    _run_worker(worker_dir, verbosity)

    for s in sites_to_upload:
        s.post_upload(puppy_dir, version)


def _resolve_zip(config: dict, puppy_dir: Path, version: str, project: Project) -> Path:
    explicit = config.get('zip')
    if explicit:
        if '{{' in explicit:
            from puppy.renderer import _env
            explicit = _env.from_string(explicit).render(config)
        p = Path(explicit) if Path(explicit).is_absolute() else (puppy_dir / explicit).resolve()
        if not p.exists():
            raise SystemExit(f'Zip not found: {p}')
        return p
    try:
        return ArtifactFinder(puppy_dir).find(project=project.pack, version=version)
    except FileNotFoundError as e:
        raise SystemExit(str(e))


def _read_auth(puppy_dir: Path) -> dict:
    auth_path = puppy_dir / 'auth.yaml'
    if not auth_path.exists():
        return {}
    return yaml.safe_load(auth_path.read_text()) or {}


def _sites_needing_upload(
    project: Project,
    config: dict,
    auth: dict,
    zip_path: Path,
    version: str,
    site: str | None,
    force: bool,
    verbosity: int,
) -> list:
    candidates = [s for s in SiteVisitor(site) if config.get(s.name, {}).get('id')]
    result = []
    for s in candidates:
        if force:
            result.append(s)
            continue
        site_id = config[s.name]['id']
        try:
            needed = s.needs_upload(site_id, auth, zip_path, version, project)
        except Exception as e:
            if verbosity >= 1:
                print(f'WARNING: could not check {s} upload status ({e}), will upload')
            needed = True
        if needed:
            result.append(s)
        elif verbosity >= 1:
            print(f'[{project.name}] {s}: already current, skipping')
    return result



def _patch_project_json(
    worker_dir: Path, project: Project, config: dict, sites_to_upload: list[str]
) -> None:
    path = worker_dir / 'projects' / project.pack / 'project.json'
    data = json.loads(path.read_text())
    data['config']['version'] = None  # bypass update.js same-version check
    data['config']['versions'] = _expand_versions(config)
    for s in SITES:
        if s not in sites_to_upload:
            data.setdefault(s.name, {})['id'] = None
    path.write_text(json.dumps(data, indent=2))


def _stage(
    project: Project, config: dict, zip_path: Path, worker_dir: Path, version: str
) -> None:
    update_dir = worker_dir / 'data' / 'update'
    if update_dir.exists():
        shutil.rmtree(update_dir)
    update_dir.mkdir(parents=True)
    update_json = {
        'id': project.pack,
        'version': version,
        'versions': _expand_versions(config),
    }
    (update_dir / 'update.json').write_text(json.dumps(update_json, indent=2))
    shutil.copy(zip_path, update_dir / 'pack.zip')


def _run_worker(worker_dir: Path, verbosity: int) -> None:
    cmd = ['node', '--no-warnings', 'scripts/update.js']
    kwargs: dict = {'cwd': worker_dir}
    if verbosity < 2:
        kwargs['capture_output'] = True
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        detail = result.stderr.decode() if verbosity < 2 else ''
        raise SystemExit(f'Worker upload failed\n{detail}'.strip())
