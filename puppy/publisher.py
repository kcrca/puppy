from pathlib import Path

import yaml

from puppy.artifacts import ArtifactFinder
from puppy.core import Project
from puppy.errors import AuthExpiredError
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SiteVisitor


def upload_file(
    *,
    project: Project,
    config: dict,
    site: str | None,
    version: str,
    force: bool,
    verbosity: int,
    auth: dict = None,
) -> None:
    if not config.get('minecraft') and not config.get('versions'):
        raise SystemExit(
            f"[{project.name}] push --file requires 'minecraft:' or 'versions:' in puppy.yaml"
        )
    puppy_dir = project.puppy_dir
    zip_path = _resolve_zip(config, puppy_dir, version, project)
    if auth is None:
        auth = _read_auth(puppy_dir)

    sites_to_upload = _sites_needing_upload(
        project, config, auth, zip_path, version, site, force, verbosity
    )
    if not sites_to_upload:
        if verbosity >= 1:
            print(
                f'[{project.name}] already current on all sites, skipping upload'
            )
        return

    mr_token = auth.get('modrinth', {}).get('token', '')
    cf_token = auth.get('curseforge', {}).get('token', '')
    pmc_cookie = auth.get('planetminecraft', '')
    pmc_id = config.get('planetminecraft', {}).get('id')

    missing = []
    if MODRINTH in sites_to_upload and not mr_token:
        missing.append(MODRINTH)
    if CURSEFORGE in sites_to_upload and not cf_token:
        missing.append(CURSEFORGE)
    if PMC in sites_to_upload and not (pmc_cookie and pmc_id):
        missing.append(PMC)
    if missing:
        labels = ', '.join(s.label for s in missing)
        raise SystemExit(f'Credentials missing for file upload: {labels} — run: puppy auth')

    if MODRINTH in sites_to_upload:
        if verbosity >= 1:
            print(f'  [Modrinth] uploading version {version}')
        mr_id = config.get('modrinth', {}).get('id') or config.get('modrinth', {}).get('slug')
        try:
            MODRINTH.upload_version(mr_id, auth, zip_path, version, config)
        except AuthExpiredError as e:
            raise SystemExit(f'Modrinth auth expired (HTTP {e.code}) — run: puppy auth --site modrinth')
        MODRINTH.post_upload(puppy_dir, version)

    if CURSEFORGE in sites_to_upload:
        if verbosity >= 1:
            print(f'  [CurseForge] uploading version {version}')
        cf_id = config.get('curseforge', {}).get('id')
        try:
            CURSEFORGE.upload_file(cf_id, auth, zip_path, version, config)
        except AuthExpiredError as e:
            raise SystemExit(f'CurseForge auth expired (HTTP {e.code}) — run: puppy auth --site cf')
        CURSEFORGE.post_upload(puppy_dir, version)

    if PMC in sites_to_upload:
        if verbosity >= 1:
            print(f'  [PlanetMinecraft] submitting version log {version}')
        try:
            PMC.submit_log(pmc_id, auth, version, config)
        except AuthExpiredError as e:
            raise SystemExit(f'PlanetMinecraft auth expired (HTTP {e.code}) — run: puppy auth --site pmc')
        PMC.post_upload(puppy_dir, version)


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

