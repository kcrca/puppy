import json
import shutil
import urllib.request
from pathlib import Path

import yaml

from puppy.core import Project
from puppy.sites import MODRINTH, SITES, SiteVisitor
from puppy.worker import read_output, run_worker


def run_import(
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
    _stage(project, config, worker_dir, site)
    _clean_existing(project, worker_dir)
    _run_worker(worker_dir, verbosity)
    result_data = read_output(project, worker_dir)
    _harvest(project, result_data, worker_dir, site, auth, images)
    if verbosity >= 1:
        print(f'[{project.name}] import complete')


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


def _harvest(
    project: Project, result_data: dict, worker_dir: Path, site: str | None,
    auth: dict, images: bool,
) -> None:
    puppy_dir = project.puppy_dir
    project_worker_dir = worker_dir / 'projects' / project.pack

    _harvest_yaml(project, result_data, puppy_dir, site, images)
    if images:
        _harvest_images(project_worker_dir, puppy_dir)
    _harvest_description(project, result_data, site, auth)


def _harvest_yaml(
    project: Project, result_data: dict, puppy_dir: Path, site: str | None,
    images: bool,
) -> None:
    puppy_yaml = puppy_dir / 'puppy.yaml'
    config = {}
    if puppy_yaml.exists():
        with puppy_yaml.open() as f:
            config = yaml.safe_load(f) or {}

    imported = result_data.get('config', {})

    # Scalars from imported config
    for key in ('name', 'summary', 'version', 'video', 'github'):
        if imported.get(key) not in (None, '', [], False):
            config[key] = imported[key]

    if images and imported.get('images'):
        image_list = [
            {**img, 'file': img['file'].strip('_')} if 'file' in img else img
            for img in imported['images']
        ]
        if (puppy_dir / 'images.yaml').exists():
            images_yaml = puppy_dir / 'images.yaml'
        else:
            images_yaml = puppy_dir / 'images' / 'images.yaml'
            images_yaml.parent.mkdir(parents=True, exist_ok=True)
        with images_yaml.open('w') as f:
            yaml.dump(
                image_list, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )
        config.pop('images', None)

    # Platform IDs/slugs and site-specific config
    for s in SiteVisitor(site):
        if s.name in result_data:
            config.setdefault(s.name, {})
            config[s.name]['id'] = result_data[s.name].get('id')
            config[s.name]['slug'] = result_data[s.name].get('slug')
        if s.name in imported:
            config.setdefault(s.name, {}).update(imported[s.name])

    puppy_yaml.parent.mkdir(parents=True, exist_ok=True)
    with puppy_yaml.open('w') as f:
        yaml.dump(
            config, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )


def _harvest_description(
    project: Project, result_data: dict, site: str | None, auth: dict
) -> None:
    visitor = SiteVisitor(site)
    if not any(s is MODRINTH for s in visitor):
        return
    modrinth_id = result_data.get('modrinth', {}).get('id')
    token = auth.get('modrinth')
    if not modrinth_id or not token:
        return
    req = urllib.request.Request(
        f'https://api.modrinth.com/v2/project/{modrinth_id}',
        headers={'Authorization': token},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    site_dir = project.puppy_dir / 'modrinth'
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / 'description.md').write_text(data['body'])


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
