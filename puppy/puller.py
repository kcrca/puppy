import json
import shutil
import urllib.request
from pathlib import Path

import yaml

from puppy.core import Project
from puppy.errors import AuthExpiredError
from puppy.sites import CURSEFORGE, MODRINTH, SITES, SiteVisitor
from puppy.worker import read_output, run_worker, worker_prep
from puppy.yaml_io import dump_puppy_yaml, load_puppy_yaml


def run_pull(
    *,
    project: Project,
    config: dict,
    auth: dict,
    worker_dir: Path,
    site: str | None,
    images: bool,
    verbosity: int,
) -> None:
    config = _resolve_ids(config, auth, site, verbosity)
    visitor = SiteVisitor(site)

    mr_token = auth.get('modrinth', {}).get('token', '')
    mr = config.get('modrinth', {})
    mr_id = mr.get('id') or mr.get('slug')
    use_mr_native = MODRINTH in visitor and bool(mr_token) and bool(mr_id)

    all_native = use_mr_native and all(s is MODRINTH for s in visitor)

    if all_native:
        _run_mr_native_pull(project, config, auth, site, images, verbosity)
    else:
        worker_prep(worker_dir, verbosity)
        _stage(project, config, worker_dir, site)
        _clean_existing(project, worker_dir)
        _run_worker(worker_dir, verbosity)
        result_data = read_output(project, worker_dir)
        _harvest(project, result_data, worker_dir, site, auth, images)

    if verbosity >= 1:
        print(f'[{project.name}] pull complete')


def _run_mr_native_pull(
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


def _resolve_ids(config: dict, auth: dict, site: str | None, verbosity: int) -> dict:
    for s in SiteVisitor(site):
        config = s.resolve_id(config, auth, verbosity)
    return config


def _stage(project: Project, config: dict, worker_dir: Path, site: str | None) -> None:
    import_data: dict = {'id': project.pack}
    visitor = SiteVisitor(site)
    for s in SITES:
        site_cfg = config.get(s.name, {})
        import_data[s.name] = {
            'id': visitor.id_or_skip(s, site_cfg.get('id')),
            'slug': site_cfg.get('slug'),
        }
    data_dir = worker_dir / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / 'import.json').write_text(json.dumps(import_data, indent=2))


def _clean_existing(project: Project, worker_dir: Path) -> None:
    existing = worker_dir / 'projects' / project.pack
    if existing.exists():
        shutil.rmtree(existing)


def _run_worker(worker_dir: Path, verbosity: int) -> None:
    run_worker('scripts/import.js', worker_dir, verbosity)


def _has_image_info(puppy_dir: Path, site: str | None) -> bool:
    dirs = [puppy_dir] + [puppy_dir / s.name for s in SiteVisitor(site)]
    return any(
        (d / 'images.yaml').exists() or (d / 'images' / 'images.yaml').exists()
        for d in dirs
    )


def _harvest(
    project: Project, result_data: dict, worker_dir: Path, site: str | None,
    auth: dict, images: bool,
) -> None:
    puppy_dir = project.puppy_dir
    project_worker_dir = worker_dir / 'projects' / project.pack

    do_images = images or not _has_image_info(puppy_dir, site)
    _harvest_description(project, result_data, site, auth)
    _harvest_yaml(project, result_data, puppy_dir, site, do_images)
    if do_images:
        _harvest_images(project_worker_dir, puppy_dir)
        _harvest_icon(project_worker_dir, puppy_dir)
        _harvest_special_images(project_worker_dir, puppy_dir)


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


def _harvest_description(
    project: Project, result_data: dict, site: str | None, auth: dict
) -> None:
    visitor = SiteVisitor(site)
    for s in visitor:
        if s is MODRINTH:
            _harvest_modrinth_description(project, result_data, auth)
        elif s is CURSEFORGE:
            _harvest_cf_description(project, result_data, auth)


def _harvest_modrinth_description(
    project: Project, result_data: dict, auth: dict
) -> None:
    modrinth_id = result_data.get('modrinth', {}).get('id')
    token = auth.get('modrinth', {}).get('token', '')
    if not modrinth_id or not token:
        return
    req = urllib.request.Request(
        f'https://api.modrinth.com/v2/project/{modrinth_id}',
        headers={'Authorization': token},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    result_data.setdefault('modrinth', {})['slug'] = data['slug']
    site_dir = project.puppy_dir / 'modrinth'
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / 'description.md').write_text(data['body'])


def _harvest_cf_description(
    project: Project, result_data: dict, auth: dict
) -> None:
    cf_id = result_data.get('curseforge', {}).get('id')
    token = auth.get('curseforge', {}).get('token')
    if not cf_id or not token:
        return
    req = urllib.request.Request(
        f'https://api.curseforge.com/v1/mods/{cf_id}/description',
        headers={'x-api-key': token},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    site_dir = project.puppy_dir / 'curseforge'
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / 'description.html').write_text(data['data'])


def _harvest_icon(project_worker_dir: Path, puppy_dir: Path) -> None:
    src = project_worker_dir / 'pack.png'
    if not src.exists():
        return
    existing = [p for p in puppy_dir.iterdir() if p.suffix == '.png' and p.name not in ('banner.png', 'logo.png')]
    if existing:
        return
    shutil.copy(src, puppy_dir / 'pack.png')


def _harvest_special_images(project_worker_dir: Path, puppy_dir: Path) -> None:
    for src_name, dest_name in (('thumbnail.png', 'banner.png'), ('logo.png', 'logo.png')):
        src = project_worker_dir / src_name
        dest = puppy_dir / dest_name
        if src.exists() and not dest.exists():
            shutil.copy(src, dest)


def _harvest_images(project_worker_dir: Path, puppy_dir: Path) -> None:
    src = project_worker_dir / 'images'
    if not src.exists():
        return
    dest = puppy_dir / 'images'
    dest.mkdir(parents=True, exist_ok=True)
    for p in dest.iterdir():
        if p.suffix != '.yaml':
            p.unlink()
    for img in src.iterdir():
        clean_name = img.stem.strip('_') + img.suffix
        shutil.copy(img, dest / clean_name)
