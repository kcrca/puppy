import shutil
from pathlib import Path

from PIL import Image

_IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tiff', '.tif']


def find_image(base: str, search_dir: Path) -> Path:
    """Locate an image file in search_dir.

    If base already has an extension, look for that exact file.
    Otherwise try recognised image extensions in priority order.
    Raises SystemExit if not found.
    """
    p = Path(base)
    if p.suffix:
        candidate = search_dir / p
        if candidate.exists():
            return candidate
        raise SystemExit(f'Image not found: {candidate}')

    for ext in _IMAGE_EXTS:
        candidate = search_dir / (base + ext)
        if candidate.exists():
            return candidate

    raise SystemExit(
        f'Image not found: {search_dir / base} (tried {", ".join(_IMAGE_EXTS)})'
    )


def stage_image(src: Path, dest: Path) -> None:
    """Copy src to dest as PNG, converting if necessary.

    dest should always end in .png (the worker requires it).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == '.png':
        shutil.copy(src, dest)
    else:
        try:
            with Image.open(src) as img:
                img.convert('RGBA').save(dest, format='PNG')
        except Exception as e:
            raise SystemExit(f'Failed to convert {src} to PNG: {e}')


def copy_images(config: dict, puppy_dir: Path, dest: Path) -> None:
    src_dir = (
        Path(config['images_source'])
        if config.get('images_source')
        else puppy_dir / 'images'
    )
    for img in config.get('images', []):
        try:
            src = find_image(img['file'], src_dir)
            stage_image(src, dest / (Path(img['file']).stem + '.png'))
        except SystemExit as e:
            print(f'WARNING: {e}')
