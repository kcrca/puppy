from pathlib import Path

import yaml

from puppy.config import ConfigSynthesizer, _deep_merge, build_projects_context
from puppy.core import Project
from puppy.creator import (
    _find_icon,
    _resolve_asset,
    _validate_square,
)
from puppy.errors import AuthExpiredError
from puppy.parallel import run_sites_parallel
from puppy.publisher import _resolve_zip, _sites_needing_upload
from puppy.renderer import render
from puppy.searcher import ContentDiscovery
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SITES, SiteVisitor

def apply_env_sides(config: dict) -> dict:
    from puppy.project_type import PROJECT_TYPES, PACK
    pt = PROJECT_TYPES.get(config.get('type', 'pack'), PACK)
    return pt.warn_inapplicable(config)


def run_push(
    *,
    project: Project,
    config: dict,
    puppy_home: Path,
    site: str | None,
    version: str | None,
    upload_file: bool,
    force: bool,
    images: bool = True,
    verbosity: int,
    auth: dict = None,
    all_labels: list[str] | None = None,
) -> None:
    config = dict(config)
    config['projects'] = build_projects_context(puppy_home)
    config = apply_env_sides(config)

    puppy_dir = project.puppy_dir
    icon = _resolve_asset(config.get('icon'), puppy_dir, _find_icon, config)
    _validate_square(icon)

    if auth is None:
        auth = _load_auth(puppy_home)
    project_type = config.get('type', 'pack')
    visitor = SiteVisitor(site, project_type=project_type)
    if verbosity >= 1 and not site:
        for s in SITES:
            if s not in visitor:
                print(f'  [{s.label}] skipping — type "{project_type}" not supported')

    cf_token = auth.get('curseforge', {}).get('token')
    cf_id = config.get('curseforge', {}).get('id')
    mr_token = auth.get('modrinth', {}).get('token', '')
    mr = config.get('modrinth', {})
    mr_id = mr.get('id') or mr.get('slug')
    pmc_cookie = auth.get('planetminecraft', '')
    pmc_id = config.get('planetminecraft', {}).get('id')

    # Upload gallery images before rendering so CDN URLs can be referenced in descriptions
    images_source = config.get('images_source')
    images_dir = Path(images_source) if images_source else puppy_dir / 'images'
    image_list = config.get('images', []) if images else []
    image_urls_by_site: dict[str, dict[str, str]] = {}
    if image_list:
        if CURSEFORGE in visitor and cf_id:
            image_urls_by_site['curseforge'] = CURSEFORGE.upload_images(
                cf_id, auth, image_list, images_dir, verbosity
            )
        if MODRINTH in visitor and mr_id:
            image_urls_by_site['modrinth'] = MODRINTH.upload_images(
                mr_id, auth, image_list, images_dir, verbosity
            )
        if PMC in visitor and pmc_id:
            image_urls_by_site['planetminecraft'] = PMC.upload_images(
                pmc_id, auth, image_list, images_dir, verbosity, project_type
            )

    discovery = ContentDiscovery(puppy_home, project.root)
    descriptions: dict[str, str] = {}
    for s in SiteVisitor(site, project_type=project_type):
        site_config = ConfigSynthesizer(
            puppy_home, project.root, site=s
        ).get_running_config()
        site_config['projects'] = config['projects']
        if s.name in site_config:
            config = _deep_merge(config, {s.name: site_config[s.name]})
        body, source = discovery.find_description(site=s)
        if body:
            rendered = render(body, site_config, source=str(source), site=s,
                              image_urls=image_urls_by_site.get(s.name))
            if source and source.suffix == '.md':
                rendered = s.convert_md(rendered)
            descriptions[s.name] = rendered

    config = dict(config)
    config['description'] = []

    missing = []
    if CURSEFORGE in visitor and cf_id and not cf_token:
        missing.append(CURSEFORGE)
    if MODRINTH in visitor and mr_id and not mr_token:
        missing.append(MODRINTH)
    if PMC in visitor and pmc_id and not pmc_cookie:
        missing.append(PMC)
    if missing:
        raise SystemExit(f'Credentials missing for: {", ".join(s.label for s in missing)} — run: puppy auth')

    zip_path = None
    sites_to_upload = set()
    if upload_file:
        if not config.get('minecraft') and not config.get('versions'):
            raise SystemExit(
                f"[{project.name}] push --file requires 'minecraft:' or 'versions:' in puppy.yaml"
            )
        zip_path = _resolve_zip(config, puppy_dir, version, project)
        sites_to_upload = set(_sites_needing_upload(project, config, auth, zip_path, version, site, force, verbosity))
        upload_missing = []
        if MODRINTH in sites_to_upload and not mr_token:
            upload_missing.append(MODRINTH)
        if CURSEFORGE in sites_to_upload and not cf_token:
            upload_missing.append(CURSEFORGE)
        if PMC in sites_to_upload and not (pmc_cookie and pmc_id):
            upload_missing.append(PMC)
        if upload_missing:
            labels = ', '.join(s.label for s in upload_missing)
            raise SystemExit(f'Credentials missing for file upload: {labels} — run: puppy auth')

    cf_zip = zip_path if CURSEFORGE in sites_to_upload else None
    mr_zip = zip_path if MODRINTH in sites_to_upload else None
    pmc_zip = zip_path if PMC in sites_to_upload else None

    def _cf_task():
        _run_cf(project, config, icon, puppy_dir, descriptions, auth, verbosity, images=images)
        if cf_zip:
            _upload_cf(cf_id, auth, cf_zip, version, config, puppy_dir, verbosity)

    def _mr_task():
        _run_mr(project, config, icon, puppy_dir, descriptions, auth, verbosity, images=images)
        if mr_zip:
            _upload_mr(mr_id, auth, mr_zip, version, config, puppy_dir, verbosity)

    def _pmc_task():
        _run_pmc(project, config, icon, puppy_dir, descriptions, auth, verbosity, images=images)
        if pmc_zip:
            _upload_pmc(pmc_id, auth, pmc_zip, version, config, puppy_dir, verbosity)

    tasks = []
    if CURSEFORGE in visitor and cf_id:
        tasks.append((CURSEFORGE.label, _cf_task))
    if MODRINTH in visitor and mr_id:
        tasks.append((MODRINTH.label, _mr_task))
    if PMC in visitor and pmc_id:
        tasks.append((PMC.label, _pmc_task))
    run_sites_parallel(tasks, all_labels=all_labels)

    if verbosity >= 1:
        print(f'[{project.name}] push complete')


def _load_auth(puppy_dir: Path) -> dict:
    auth_path = puppy_dir / 'auth.yaml'
    if not auth_path.exists():
        return {}
    return yaml.safe_load(auth_path.read_text()) or {}


def _run_cf(
    project: Project,
    config: dict,
    icon: Path,
    puppy_dir: Path,
    descriptions: dict,
    auth: dict,
    verbosity: int,
    images: bool = True,
) -> None:
    project_id = config.get('curseforge', {}).get('id')
    description = descriptions.get('curseforge', '')
    images_source = config.get('images_source')
    images_dir = Path(images_source) if images_source else puppy_dir / 'images'
    image_list = config.get('images', []) if images else []

    try:
        CURSEFORGE.push(
            project_id=project_id,
            config=config,
            description=description,
            icon_path=icon,
            logo_path=None,
            banner_path=None,
            image_list=image_list,
            images_dir=images_dir,
            auth=auth,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'CurseForge auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site cf')


def _upload_cf(
    project_id,
    auth: dict,
    zip_path: Path,
    version: str,
    config: dict,
    puppy_dir: Path,
    verbosity: int,
) -> None:
    try:
        if verbosity >= 1:
            print(f'  [CurseForge] uploading version {version}')
        CURSEFORGE.upload_file(project_id, auth, zip_path, version, config)
        CURSEFORGE.post_upload(puppy_dir, version)
    except AuthExpiredError as e:
        raise SystemExit(f'CurseForge auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site cf')


def _run_mr(
    project: Project,
    config: dict,
    icon: Path,
    puppy_dir: Path,
    descriptions: dict,
    auth: dict,
    verbosity: int,
    images: bool = True,
) -> None:
    mr = config.get('modrinth', {})
    project_id = mr.get('id') or mr.get('slug')
    description = descriptions.get('modrinth', '')
    images_source = config.get('images_source')
    images_dir = Path(images_source) if images_source else puppy_dir / 'images'
    image_list = config.get('images', []) if images else []

    try:
        MODRINTH.push(
            project_id=project_id,
            config=config,
            description=description,
            icon_path=icon,
            logo_path=None,
            banner_path=None,
            image_list=image_list,
            images_dir=images_dir,
            auth=auth,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'Modrinth auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site modrinth')


def _upload_mr(
    project_id,
    auth: dict,
    zip_path: Path,
    version: str,
    config: dict,
    puppy_dir: Path,
    verbosity: int,
) -> None:
    try:
        if verbosity >= 1:
            print(f'  [Modrinth] uploading version {version}')
        MODRINTH.upload_version(project_id, auth, zip_path, version, config)
        MODRINTH.post_upload(puppy_dir, version)
    except AuthExpiredError as e:
        raise SystemExit(f'Modrinth auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site modrinth')


def _run_pmc(
    project: Project,
    config: dict,
    icon: Path,
    puppy_dir: Path,
    descriptions: dict,
    auth: dict,
    verbosity: int,
    images: bool = True,
) -> None:
    pmc = config.get('planetminecraft', {})
    project_id = pmc.get('id')
    description = descriptions.get('planetminecraft', '')
    images_source = config.get('images_source')
    images_dir = Path(images_source) if images_source else puppy_dir / 'images'
    image_list = config.get('images', []) if images else []

    try:
        PMC.push(
            project_id=project_id,
            config=config,
            description=description,
            icon_path=icon,
            logo_path=None,
            banner_path=None,
            image_list=image_list,
            images_dir=images_dir,
            auth=auth,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'PlanetMinecraft auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site pmc')


def _upload_pmc(
    project_id,
    auth: dict,
    zip_path: Path,
    version: str,
    config: dict,
    puppy_dir: Path,
    verbosity: int,
) -> None:
    try:
        if verbosity >= 1:
            print(f'  [PlanetMinecraft] submitting version log {version}')
        PMC.submit_log(project_id, auth, version, config)
        PMC.post_upload(puppy_dir, version)
    except AuthExpiredError as e:
        raise SystemExit(f'PlanetMinecraft auth expired (HTTP {e.code}: {e.body[:200]}) — run: puppy auth --site pmc')


