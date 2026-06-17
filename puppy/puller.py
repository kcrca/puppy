from pathlib import Path

import yaml

from puppy.core import Project
from puppy.errors import AuthExpiredError, prefix_site_error
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SITES, SiteVisitor
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
    project_type = config.get('type', 'pack')
    config = _resolve_ids(config, auth, site, verbosity, project_type)
    visitor = SiteVisitor(site, project_type=project_type)

    missing = [s for s in SITES if s in visitor and s.ref(config) and not s.has_credentials(auth)]
    if missing:
        raise SystemExit(f'Credentials missing for: {", ".join(s.label for s in missing)} — run: puppy auth')

    puppy_dir = project.puppy_dir
    results = []

    # MR first, then CF, then PMC (download-link / merge order).
    for s, runner in ((MODRINTH, _run_mr_pull), (CURSEFORGE, _run_cf_pull), (PMC, _run_pmc_pull)):
        if s not in visitor or not s.ref(config):
            continue
        try:
            r = runner(project, config, auth, site, images, verbosity)
        except SystemExit as e:
            raise prefix_site_error(s.label, e) from None
        if r is not None:
            results.append(r)

    if results:
        _harvest_yaml(project, _merge_results(results), puppy_dir, site, images, project_type)

    if verbosity >= 1:
        print(f'[{project.name}] pull complete')


def _run_mr_pull(
    project: Project,
    config: dict,
    auth: dict,
    site: str | None,
    images: bool,
    verbosity: int,
) -> dict:
    mr = config.get('modrinth', {})
    project_id = mr.get('id') or mr.get('slug')
    puppy_dir = project.puppy_dir
    project_type = config.get('type', 'pack')
    do_images = images or not _has_image_info(puppy_dir, site, project_type)

    try:
        return MODRINTH.pull(
            project_id=project_id,
            auth=auth,
            puppy_dir=puppy_dir,
            images=do_images,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'Modrinth auth expired (HTTP {e.code}) — run: puppy auth --site modrinth')


def _run_cf_pull(
    project: Project,
    config: dict,
    auth: dict,
    site: str | None,
    images: bool,
    verbosity: int,
) -> dict:
    cf_id = config.get('curseforge', {}).get('id')
    puppy_dir = project.puppy_dir
    project_type = config.get('type', 'pack')
    do_images = images or not _has_image_info(puppy_dir, site, project_type)

    try:
        return CURSEFORGE.pull(
            project_id=cf_id,
            auth=auth,
            puppy_dir=puppy_dir,
            images=do_images,
            verbosity=verbosity,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'CurseForge auth expired (HTTP {e.code}) — run: puppy auth --site cf')


def _run_pmc_pull(
    project: Project,
    config: dict,
    auth: dict,
    site: str | None,
    images: bool,
    verbosity: int,
) -> dict:
    pmc_id = config.get('planetminecraft', {}).get('id')
    puppy_dir = project.puppy_dir
    project_type = config.get('type', 'pack')
    do_images = images or not _has_image_info(puppy_dir, site, project_type)

    try:
        return PMC.pull(
            project_id=pmc_id,
            auth=auth,
            puppy_dir=puppy_dir,
            images=do_images,
            verbosity=verbosity,
            project_type=project_type,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'PlanetMinecraft auth expired (HTTP {e.code}) — run: puppy auth --site pmc')


def _merge_results(results: list[dict]) -> dict:
    merged: dict = {}
    merged_config: dict = {}
    for r in results:
        for k, v in r.items():
            if k == 'config':
                for ck, cv in v.items():
                    if cv not in (None, '', [], False):
                        merged_config[ck] = cv
            else:
                merged[k] = v
    if merged_config:
        merged['config'] = merged_config
    return merged


def _resolve_ids(config: dict, auth: dict, site: str | None, verbosity: int, project_type: str = 'pack') -> dict:
    for s in SiteVisitor(site, project_type=project_type):
        try:
            config = s.resolve_id(config, auth, verbosity)
        except SystemExit as e:
            raise prefix_site_error(s.label, e) from None
    return config


def _has_image_info(puppy_dir: Path, site: str | None, project_type: str = 'pack') -> bool:
    dirs = [puppy_dir] + [puppy_dir / s.name for s in SiteVisitor(site, project_type=project_type)]
    return any(
        (d / 'images.yaml').exists() or (d / 'images' / 'images.yaml').exists()
        for d in dirs
    )


def _harvest_yaml(
    project: Project, result_data: dict, puppy_dir: Path, site: str | None,
    images: bool, project_type: str = 'pack',
) -> None:
    puppy_yaml = puppy_dir / 'puppy.yaml'
    config = load_puppy_yaml(puppy_yaml)

    imported = result_data.get('config', {})

    # Scalars from imported config
    for key in ('name', 'summary', 'optifine', 'video', 'github'):
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

    if imported.get('images') and (images or not _has_image_info(puppy_dir, site, project_type)):
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
    for s in SiteVisitor(site, project_type=project_type):
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

    # Promote license to neutral if all sites agree (normalized to SPDX)
    site_licenses = {}
    for s in SiteVisitor(site, project_type=project_type):
        if s.name in result_data:
            site_lic = result_data[s.name].get('license')
            if site_lic:
                spdx = s.spdx_license(site_lic)
                if spdx and not spdx.startswith('LicenseRef-'):
                    site_licenses[s.name] = spdx
    if site_licenses and len(set(site_licenses.values())) == 1:
        config['license'] = next(iter(site_licenses.values()))

    dump_puppy_yaml(config, puppy_yaml)


