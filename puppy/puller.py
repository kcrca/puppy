from pathlib import Path

import yaml

from puppy.core import Project
from puppy.errors import AuthExpiredError, prefix_site_error
from puppy.parallel import run_sites_parallel
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
    project_type = config.get('type', 'pack')
    config = _resolve_ids(config, auth, site, verbosity, project_type)
    visitor = SiteVisitor(site, project_type=project_type)
    puppy_dir = project.puppy_dir

    # MR first, then CF, then PMC. The first present site is the single source for
    # the shared image library + icon; the rest pull descriptions/metadata only.
    pull_sites = [s for s in (MODRINTH, CURSEFORGE, PMC) if s in visitor and s.ref(config)]

    missing = [s for s in pull_sites if not s.has_credentials(auth)]
    if missing:
        raise SystemExit(f'Credentials missing for: {", ".join(s.label for s in missing)} — run: puppy auth')

    if pull_sites:
        designated = pull_sites[0]
        want_assets = images or not _has_image_info(puppy_dir, site, project_type)

        def _make_task(s):
            download = (s is designated) and want_assets
            return lambda: _run_pull(s, project, config, auth, download, verbosity, project_type)

        tasks = [(s.label, _make_task(s)) for s in pull_sites]
        results_by_label = run_sites_parallel(tasks, verbosity=verbosity)

        # Single image source: drop image metadata from non-designated sites so the
        # library comes only from the site that actually downloaded the files.
        for label, r in results_by_label.items():
            if label != designated.label and isinstance(r, dict):
                r.pop('images', None)

        results = list(results_by_label.values())
        if results:
            _harvest_yaml(project, _merge_results(results), puppy_dir, site, images, project_type)

    if verbosity >= 1:
        print(f'[{project.name}] pull complete')


def _run_pull(
    s,
    project: Project,
    config: dict,
    auth: dict,
    download: bool,
    verbosity: int,
    project_type: str,
) -> dict:
    try:
        return s.pull(
            project_id=s.ref(config),
            auth=auth,
            puppy_dir=project.puppy_dir,
            images=download,
            verbosity=verbosity,
            project_type=project_type,
        )
    except AuthExpiredError as e:
        raise SystemExit(f'{s.label} auth expired (HTTP {e.code}) — run: puppy auth --site {s.auth_arg}')


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


