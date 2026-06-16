from pathlib import Path

import yaml

from puppy.artifacts import ArtifactFinder
from puppy.core import Project
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SiteVisitor


def _resolve_zip(config: dict, puppy_dir: Path, version: str, project: Project) -> Path:
    explicit = config.get('file')
    if explicit:
        p = Path(explicit) if Path(explicit).is_absolute() else (puppy_dir / explicit).resolve()
        if not p.exists():
            raise SystemExit(f'Zip not found: {p}')
        return p
    try:
        return ArtifactFinder(puppy_dir).find(project=project.handle, version=version)
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
    candidates = [s for s in SiteVisitor(site) if config.get(s.name, {}).get('id')
                  and not (s.name == 'planetminecraft' and config.get('planetminecraft', {}).get('download'))]
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

