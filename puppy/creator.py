import json
import shutil
from pathlib import Path

import yaml
from PIL import Image

from puppy.core import Project
from puppy.images import copy_images, stage_image
from puppy.sites import SITES, SiteVisitor
from puppy.worker import read_output, run_worker


def run_create(
    *,
    project: Project,
    config: dict,
    worker_dir: Path,
    site: str | None,
    verbosity: int,
) -> None:
    puppy_dir = project.root / 'puppy'
    icon = _resolve_asset(config.get('icon'), puppy_dir, _find_icon)
    zip_path = _resolve_asset(config.get('zip'), puppy_dir, _find_zip)
    _validate_square(icon)
    _stage(project, config, icon, zip_path, puppy_dir, worker_dir, site)
    _run_worker(worker_dir, verbosity)
    result_data = read_output(project, worker_dir)
    _harvest(project, result_data, site)
    if verbosity >= 1:
        print(f'[{project.name}] create complete')


def _resolve_asset(explicit: str | None, puppy_dir: Path, discover_fn) -> Path:
    if explicit:
        p = (puppy_dir / explicit).resolve()
        if not p.exists():
            raise SystemExit(f'Asset not found: {p}')
        return p
    return discover_fn(puppy_dir)


def _find_icon(puppy_dir: Path) -> Path:
    pngs = [
        p
        for p in puppy_dir.iterdir()
        if p.suffix == '.png' and p.name not in ('thumbnail.png', 'logo.png')
    ]
    if len(pngs) == 1:
        return pngs[0]
    if not pngs:
        raise SystemExit(f'No icon PNG found in {puppy_dir}')
    raise SystemExit(
        f'Multiple PNG files in {puppy_dir} — ambiguous icon: {[p.name for p in pngs]}'
    )


def _find_zip(puppy_dir: Path) -> Path:
    zips = list(puppy_dir.glob('*.zip'))
    if len(zips) == 1:
        return zips[0]
    if not zips:
        raise SystemExit(f'No ZIP file found in {puppy_dir}')
    raise SystemExit(
        f'Multiple ZIP files in {puppy_dir} — ambiguous artifact: {[p.name for p in zips]}'
    )


def _validate_square(icon: Path) -> None:
    try:
        with Image.open(icon) as img:
            w, h = img.size
    except Exception as e:
        raise SystemExit(f'Icon {icon.name} could not be read: {e}')
    if w != h:
        raise SystemExit(f'Icon {icon.name} must be square ({w}x{h})')


def _expand_versions(config: dict) -> dict:
    minecraft = config.get('minecraft')
    explicit = config.get('versions', {})
    if not minecraft:
        return explicit
    base = (
        {'type': 'exact', 'version': str(minecraft)}
        if not isinstance(minecraft, dict)
        else minecraft
    )
    return {s.name: explicit.get(s.name, base) for s in SITES}


def _build_config(project: Project, config: dict) -> dict:
    def _site_config(s: str) -> dict:
        return {k: v for k, v in config.get(s, {}).items() if k not in ('id', 'slug')}

    return {
        'id': project.pack,
        'name': project.name,
        'summary': config.get('summary', ''),
        'description': config.get('description', []),
        'optifine': config.get('optifine', False),
        'video': config.get('video', False),
        'github': config.get('github', False),
        'version': config.get('version', '1.0.0'),
        'versions': _expand_versions(config),
        'images': config.get('images', []),
        **{s.name: _site_config(s.name) for s in SITES},
    }


def _stage(
    project: Project,
    config: dict,
    icon: Path,
    zip_path: Path,
    puppy_dir: Path,
    worker_dir: Path,
    site: str | None,
) -> None:
    cfg = _build_config(project, config)

    # data/create/
    data_dir = worker_dir / 'data' / 'create'
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True)

    (data_dir / 'create.json').write_text(json.dumps(cfg, indent=2))
    stage_image(icon, data_dir / 'pack.png')
    shutil.copy(zip_path, data_dir / 'pack.zip')

    copy_images(config, puppy_dir, data_dir / 'images')

    for optional in ('thumbnail.png', 'logo.png'):
        src = puppy_dir / optional
        if src.exists():
            shutil.copy(src, data_dir / optional)

    # Pre-stage projects/{pack}/ so existing IDs are preserved
    project_dir = worker_dir / 'projects' / project.pack
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True)

    visitor = SiteVisitor(site)
    existing = {
        s.name: {
            'id': visitor.id_or_skip(s, config.get(s.name, {}).get('id')),
            'slug': config.get(s.name, {}).get('slug', 'my-project'),
        }
        for s in SITES
    }
    project_json = {'config': cfg, **existing}
    (project_dir / 'project.json').write_text(json.dumps(project_json, indent=2))

    stage_image(icon, project_dir / 'pack.png')
    copy_images(config, puppy_dir, project_dir / 'images')

    for optional in ('thumbnail.png', 'logo.png'):
        src = puppy_dir / optional
        if src.exists():
            shutil.copy(src, project_dir / optional)


def _run_worker(worker_dir: Path, verbosity: int) -> None:
    run_worker('scripts/create.js', worker_dir, verbosity)


def _harvest(project: Project, result_data: dict, site: str | None) -> None:
    puppy_yaml = project.root / 'puppy' / 'puppy.yaml'
    config: dict = {}
    if puppy_yaml.exists():
        config = yaml.safe_load(puppy_yaml.read_text()) or {}

    for s in SiteVisitor(site):
        platform_data = result_data.get(s.name, {})
        harvested_id = platform_data.get('id')
        if harvested_id and harvested_id != '__skip__':
            config.setdefault(s.name, {})
            config[s.name]['id'] = harvested_id
            config[s.name]['slug'] = platform_data.get('slug')

    with puppy_yaml.open('w') as f:
        yaml.dump(
            config, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
