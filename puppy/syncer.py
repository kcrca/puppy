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
from puppy.publisher import upload_pack
from puppy.renderer import render
from puppy.searcher import ContentDiscovery
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SiteVisitor


def run_push(
    *,
    project: Project,
    config: dict,
    puppy_home: Path,
    site: str | None,
    version: str | None,
    pack: bool,
    force: bool,
    images: bool = True,
    verbosity: int,
    auth: dict = None,
) -> None:
    config = dict(config)
    config['projects'] = build_projects_context(puppy_home)

    puppy_dir = project.puppy_dir
    icon = _resolve_asset(config.get('icon'), puppy_dir, _find_icon, config)
    _validate_square(icon)

    discovery = ContentDiscovery(puppy_home, project.root)
    descriptions: dict[str, str] = {}
    for s in SiteVisitor(site):
        site_config = ConfigSynthesizer(
            puppy_home, project.root, site=s
        ).get_running_config()
        site_config['projects'] = config['projects']
        if s.name in site_config:
            config = _deep_merge(config, {s.name: site_config[s.name]})
        body, source = discovery.find_description(site=s)
        if body:
            rendered = render(body, site_config, source=str(source), site=s)
            if source and source.suffix == '.md':
                rendered = s.convert_md(rendered)
            descriptions[s.name] = rendered

    config = dict(config)
    config['description'] = []

    if auth is None:
        auth = _load_auth(puppy_home)
    visitor = SiteVisitor(site)

    cf_token = auth.get('curseforge', {}).get('token')
    cf_id = config.get('curseforge', {}).get('id')
    mr_token = auth.get('modrinth', {}).get('token', '')
    mr = config.get('modrinth', {})
    mr_id = mr.get('id') or mr.get('slug')
    pmc_cookie = auth.get('planetminecraft', '')
    pmc_id = config.get('planetminecraft', {}).get('id')

    missing = []
    if CURSEFORGE in visitor and cf_id and not cf_token:
        missing.append(CURSEFORGE)
    if MODRINTH in visitor and mr_id and not mr_token:
        missing.append(MODRINTH)
    if PMC in visitor and pmc_id and not pmc_cookie:
        missing.append(PMC)
    if missing:
        raise SystemExit(f'Credentials missing for: {", ".join(s.label for s in missing)} — run: puppy auth')

    if CURSEFORGE in visitor and cf_id:
        _run_cf(project, config, icon, puppy_dir, descriptions, auth, verbosity, images=images)
    if MODRINTH in visitor and mr_id:
        _run_mr(project, config, icon, puppy_dir, descriptions, auth, verbosity, images=images)
    if PMC in visitor and pmc_id:
        _run_pmc(project, config, icon, puppy_dir, descriptions, auth, verbosity, images=images)

    if pack:
        upload_pack(
            project=project,
            config=config,
            site=site,
            version=version,
            force=force,
            verbosity=verbosity,
            auth=auth,
        )

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


