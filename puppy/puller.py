from pathlib import Path

import yaml

from puppy.core import Project
from puppy.errors import AuthExpiredError
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SiteVisitor
from puppy.yaml_io import dump_puppy_yaml, load_puppy_yaml


def run_pull(
    *,
    project: Project,
    config: dict,
    auth: dict,
    site: str | None,
    images: bool,
    verbosity: int,
) -> None:
    config = _resolve_ids(config, auth, site, verbosity)
    visitor = SiteVisitor(site)

    mr_token = auth.get('modrinth', {}).get('token', '')
    mr = config.get('modrinth', {})
    mr_id = mr.get('id') or mr.get('slug')
    cf_token = auth.get('curseforge', {}).get('token')
    cf_cookie = auth.get('curseforge', {}).get('cookie')
    cf_id = config.get('curseforge', {}).get('id')
    pmc_cookie = auth.get('planetminecraft', '')
    pmc_id = config.get('planetminecraft', {}).get('id')

    missing = []
    if MODRINTH in visitor and mr_id and not mr_token:
        missing.append(MODRINTH)
    if CURSEFORGE in visitor and cf_id and not (cf_token and cf_cookie):
        missing.append(CURSEFORGE)
    if PMC in visitor and pmc_id and not pmc_cookie:
        missing.append(PMC)
    if missing:
        raise SystemExit(f'Credentials missing for: {", ".join(s.label for s in missing)} — run: puppy auth')

    if MODRINTH in visitor and mr_id:
        _run_mr_pull(project, config, auth, site, images, verbosity)
    if CURSEFORGE in visitor and cf_id:
        _run_cf_pull(project, config, auth, site, images, verbosity)
    if PMC in visitor and pmc_id:
        _run_pmc_pull(project, config, auth, site, images, verbosity)

    if verbosity >= 1:
        print(f'[{project.name}] pull complete')


def _run_mr_pull(
    project: Project,
    config: dict,
    auth: dict,
    site: str | None,
    images: bool,
    verbosity: int,
) -> None:
    mr = config.get('modrinth', {})
    project_id = mr.get('id') or mr.get('slug')
    puppy_dir = project.puppy_dir
    do_images = images or not _has_image_info(puppy_dir, site)

    try:
        result_data = MODRINTH.pull(
            project_id=project_id,
            auth=auth,
            puppy_dir=puppy_dir,
            images=do_images,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'Modrinth auth expired (HTTP {e.code}) — run: puppy auth --site modrinth')

    _harvest_yaml(project, result_data, puppy_dir, site, do_images)


def _run_cf_pull(
    project: Project,
    config: dict,
    auth: dict,
    site: str | None,
    images: bool,
    verbosity: int,
) -> None:
    cf_id = config.get('curseforge', {}).get('id')
    puppy_dir = project.puppy_dir
    do_images = images or not _has_image_info(puppy_dir, site)

    try:
        result_data = CURSEFORGE.pull(
            project_id=cf_id,
            auth=auth,
            puppy_dir=puppy_dir,
            images=do_images,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'CurseForge auth expired (HTTP {e.code}) — run: puppy auth --site cf')

    _harvest_yaml(project, result_data, puppy_dir, site, do_images)


def _run_pmc_pull(
    project: Project,
    config: dict,
    auth: dict,
    site: str | None,
    images: bool,
    verbosity: int,
) -> None:
    pmc_id = config.get('planetminecraft', {}).get('id')
    puppy_dir = project.puppy_dir
    do_images = images or not _has_image_info(puppy_dir, site)

    try:
        result_data = PMC.pull(
            project_id=pmc_id,
            auth=auth,
            puppy_dir=puppy_dir,
            images=do_images,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'PlanetMinecraft auth expired (HTTP {e.code}) — run: puppy auth --site pmc')

    _harvest_yaml(project, result_data, puppy_dir, site, do_images)


def _resolve_ids(config: dict, auth: dict, site: str | None, verbosity: int) -> dict:
    for s in SiteVisitor(site):
        config = s.resolve_id(config, auth, verbosity)
    return config


def _has_image_info(puppy_dir: Path, site: str | None) -> bool:
    dirs = [puppy_dir] + [puppy_dir / s.name for s in SiteVisitor(site)]
    return any(
        (d / 'images.yaml').exists() or (d / 'images' / 'images.yaml').exists()
        for d in dirs
    )


def _harvest_yaml(
    project: Project, result_data: dict, puppy_dir: Path, site: str | None,
    images: bool,
) -> None:
    puppy_yaml = puppy_dir / 'puppy.yaml'
    config = load_puppy_yaml(puppy_yaml)

    imported = result_data.get('config', {})

    # Scalars from imported config
    for key in ('name', 'summary', 'license', 'optifine', 'video', 'github'):
        if imported.get(key) not in (None, '', [], False):
            config[key] = imported[key]

    # Dict merges: only add non-null values, don't wipe existing keys
    for key in ('links', 'socials'):
        val = imported.get(key)
        if val and isinstance(val, dict):
            existing = config.setdefault(key, {})
            for k, v in val.items():
                if v:
                    existing[k] = v

    if images and imported.get('images'):
        image_list = [
            {**img, 'file': img['file'].strip('_')} if 'file' in img else img
            for img in imported['images']
        ]
        images_yaml = puppy_dir / 'images' / 'images.yaml'
        images_yaml.parent.mkdir(parents=True, exist_ok=True)
        (puppy_dir / 'images.yaml').unlink(missing_ok=True)
        with images_yaml.open('w') as f:
            yaml.dump(
                image_list, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )
        config.pop('images', None)

    # Platform IDs/slugs and site-specific config
    for s in SiteVisitor(site):
        if s.name in result_data:
            site_cfg = config.setdefault(s.name, {})
            for k, v in result_data[s.name].items():
                if v is not None:
                    if k not in site_cfg and hasattr(site_cfg, 'insert'):
                        site_cfg.insert(0, k, v)
                    else:
                        site_cfg[k] = v
        if s.name in imported:
            config.setdefault(s.name, {}).update(imported[s.name])

    dump_puppy_yaml(config, puppy_yaml)


