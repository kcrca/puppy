from pathlib import Path

import yaml
from PIL import Image

from puppy.core import Project
from puppy.images import prepare_icon
from puppy.sites import CURSEFORGE, MODRINTH, PMC, SITES, SiteVisitor
from puppy.yaml_io import dump_puppy_yaml, load_puppy_yaml


def _resolve_asset(explicit: str | None, puppy_dir: Path, discover_fn, config: dict = None) -> Path:
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
        if p.suffix == '.png' and p.name not in ('banner.png', 'logo.png')
    ]
    if len(pngs) == 1:
        return pngs[0]
    if not pngs:
        raise SystemExit(f'No icon PNG found in {puppy_dir}')
    raise SystemExit(
        f'Multiple PNG files in {puppy_dir} — ambiguous icon: {[p.name for p in pngs]}'
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


def run_create(
    *,
    project: Project,
    config: dict,
    puppy_home: Path,
    auth: dict,
    site: str | None,
    images: bool,
    verbosity: int,
) -> None:
    from puppy.errors import AuthExpiredError
    from puppy.syncer import run_push

    puppy_dir = project.puppy_dir
    icon = _resolve_asset(config.get('icon'), puppy_dir, _find_icon, config)
    _validate_square(icon)
    icon_bytes = prepare_icon(icon)

    puppy_yaml = puppy_dir / 'puppy.yaml'
    visitor = SiteVisitor(site)

    cf_token = auth.get('curseforge', {}).get('token')
    cf_cookie = auth.get('curseforge', {}).get('cookie')
    mr_token = auth.get('modrinth', {}).get('token', '')
    pmc_cookie = auth.get('planetminecraft', '')

    missing = []
    if CURSEFORGE in visitor and not config.get('curseforge', {}).get('id') and not (cf_token and cf_cookie):
        missing.append(CURSEFORGE)
    if MODRINTH in visitor and not config.get('modrinth', {}).get('id') and not mr_token:
        missing.append(MODRINTH)
    if PMC in visitor and not config.get('planetminecraft', {}).get('id') and not pmc_cookie:
        missing.append(PMC)
    if missing:
        raise SystemExit(f'Credentials missing for: {", ".join(s.label for s in missing)} — run: puppy auth')

    config = dict(config)

    # CF first so PMC can use the slug in the download link
    if CURSEFORGE in visitor and not config.get('curseforge', {}).get('id'):
        if verbosity >= 1:
            print(f'[{project.name}] CurseForge: creating project')
        try:
            result = CURSEFORGE.create(config=config, auth=auth, icon_bytes=icon_bytes, verbosity=verbosity)
        except AuthExpiredError as e:
            raise SystemExit(f'CurseForge auth expired (HTTP {e.code}) — run: puppy auth --site cf')
        _update_config(puppy_yaml, 'curseforge', result)
        config.setdefault('curseforge', {}).update(result)

    # MR second
    if MODRINTH in visitor and not config.get('modrinth', {}).get('id'):
        if verbosity >= 1:
            print(f'[{project.name}] Modrinth: creating project')
        try:
            result = MODRINTH.create(config=config, auth=auth, verbosity=verbosity)
        except AuthExpiredError as e:
            raise SystemExit(f'Modrinth auth expired (HTTP {e.code}) — run: puppy auth --site modrinth')
        _update_config(puppy_yaml, 'modrinth', result)
        config.setdefault('modrinth', {}).update(result)

    # PMC last (uses MR/CF slugs for download link)
    if PMC in visitor and not config.get('planetminecraft', {}).get('id'):
        if verbosity >= 1:
            print(f'[{project.name}] PlanetMinecraft: creating project')
        images_source = config.get('images_source')
        images_dir = Path(images_source) if images_source else puppy_dir / 'images'
        image_list = config.get('images', []) if images else []
        try:
            result = PMC.create(
                config=config,
                auth=auth,
                image_list=image_list,
                images_dir=images_dir,
                verbosity=verbosity,
            )
        except AuthExpiredError as e:
            raise SystemExit(f'PlanetMinecraft auth expired (HTTP {e.code}) — run: puppy auth --site pmc')
        _update_config(puppy_yaml, 'planetminecraft', result)
        config.setdefault('planetminecraft', {}).update(result)

    # Push to populate descriptions, icon, gallery, details
    run_push(
        project=project,
        config=config,
        puppy_home=puppy_home,
        site=site,
        version=None,
        pack=False,
        force=False,
        images=images,
        verbosity=verbosity,
        auth=auth,
    )

    if verbosity >= 1:
        print(f'[{project.name}] create complete')


def _update_config(puppy_yaml: Path, key: str, values: dict) -> None:
    existing = load_puppy_yaml(puppy_yaml)
    existing.setdefault(key, {}).update(values)
    dump_puppy_yaml(existing, puppy_yaml)


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


