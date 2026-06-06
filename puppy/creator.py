from pathlib import Path

from PIL import Image

from puppy.core import Project
from puppy.sites import SITES


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


