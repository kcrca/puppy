import json
import shutil
from pathlib import Path

import yaml

from puppy.config import ConfigSynthesizer, _deep_merge, build_projects_context
from puppy.core import Project
from puppy.creator import (
    _build_config,
    _find_icon,
    _resolve_asset,
    _resolve_optional_asset,
    _validate_square,
)
from puppy.errors import AuthExpiredError
from puppy.images import copy_images, stage_image
from puppy.publisher import upload_pack
from puppy.renderer import render
from puppy.searcher import ContentDiscovery
from puppy.sites import CURSEFORGE, SITES, SiteVisitor
from puppy.worker import run_worker


def run_push(
    *,
    project: Project,
    config: dict,
    worker_dir: Path,
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
    cf_token = auth.get('curseforge', {}).get('token')
    visitor = SiteVisitor(site)
    cf_id = config.get('curseforge', {}).get('id')
    use_cf_native = CURSEFORGE in visitor and bool(cf_token) and bool(cf_id)

    if use_cf_native:
        _run_cf_native(project, config, icon, puppy_dir, descriptions, auth, verbosity, images=images)

    cf_only = use_cf_native and all(s is CURSEFORGE for s in visitor)
    needs_worker = not cf_only or pack
    if needs_worker:
        _stage(project, config, icon, puppy_dir, worker_dir, site, descriptions, images=images)
        if not cf_only:
            _run_worker(worker_dir, verbosity)

    if pack:
        upload_pack(
            project=project,
            config=config,
            worker_dir=worker_dir,
            site=site,
            version=version,
            force=force,
            verbosity=verbosity,
        )

    if verbosity >= 1:
        print(f'[{project.name}] push complete')


def _load_auth(puppy_dir: Path) -> dict:
    auth_path = puppy_dir / 'auth.yaml'
    if not auth_path.exists():
        return {}
    return yaml.safe_load(auth_path.read_text()) or {}


def _run_cf_native(
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


def _stage(
    project: Project,
    config: dict,
    icon: Path,
    puppy_dir: Path,
    worker_dir: Path,
    site: str | None,
    descriptions: dict[str, str] = None,
    images: bool = True,
) -> None:
    cfg = _build_config(project, config)

    # data/details.json
    data_dir = worker_dir / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    details = {'id': project.pack, 'images': images, 'live': True}
    (data_dir / 'details.json').write_text(json.dumps(details, indent=2))

    # projects/{pack}/
    project_dir = worker_dir / 'projects' / project.pack
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True)

    visitor = SiteVisitor(site)
    platform_ids = {
        s.name: {
            'id': visitor.id_or_skip(s, config.get(s.name, {}).get('id')),
            'slug': config.get(s.name, {}).get('slug'),
        }
        for s in SITES
    }
    project_json = {'config': cfg, **platform_ids}
    (project_dir / 'project.json').write_text(json.dumps(project_json, indent=2))

    stage_image(icon, project_dir / 'pack.png')

    copy_images(config, puppy_dir, project_dir / 'images')

    for src_name, dest_name, key in (('banner.png', 'thumbnail.png', 'banner'), ('logo.png', 'logo.png', 'logo')):
        src = _resolve_optional_asset(config.get(key), src_name, puppy_dir, config)
        if src:
            shutil.copy(src, project_dir / dest_name)

    _stage_templates(project_dir, puppy_dir, site, descriptions or {})


_MINIMAL_TEMPLATE = {
    '.md': '{{ description }}\n\n{{ images }}\n',
    '.html': '{{ description }}\n\n{{ images }}\n',
    '.bbcode': '{{ description }}\n\n{{ images }}\n',
}



def _stage_templates(
    project_dir: Path, puppy_dir: Path, site: str | None, descriptions: dict[str, str]
) -> None:
    templates_dir = project_dir / 'templates'
    templates_dir.mkdir()
    visitor = SiteVisitor(site)
    for s in visitor:
        ext = s.template_ext
        dest = templates_dir / f'{s.name}{ext}'
        src = puppy_dir / s.name / f'description{ext}'
        rendered = descriptions.get(s.name)
        if rendered is not None:
            # Bake rendered description; leave {{ images }} for the worker
            dest.write_text(f'{rendered}\n\n{{{{ images }}}}\n')
        elif src.exists():
            shutil.copy(src, dest)
        else:
            dest.write_text(_MINIMAL_TEMPLATE[ext])


def _run_worker(worker_dir: Path, verbosity: int) -> None:
    run_worker('scripts/details.js', worker_dir, verbosity, stream=True)
