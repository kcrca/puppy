import shutil
from io import BytesIO
from pathlib import Path

from PIL import Image

_ICON_SIZE = (512, 512)
_GALLERY_SIZE = (1920, 1080)
_LOGO_SIZE = (1280, 256)

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


def prepare_icon(src: Path, verbosity: int = 0) -> bytes:
    try:
        img_obj = Image.open(src)
    except Exception as e:
        raise SystemExit(f'Failed to read icon {src}: {e}')
    with img_obj as img:
        w, h = img.size
        if w != h:
            print(f'Warning: icon {src.name} is not square ({w}×{h}) — padding to 512×512')
        scale = min(_ICON_SIZE[0] / w, _ICON_SIZE[1] / h)
        new_size = (round(w * scale), round(h * scale))
        scaled = img.convert('RGBA').resize(new_size, Image.LANCZOS)
    canvas = Image.new('RGBA', _ICON_SIZE, (0, 0, 0, 0))
    offset = ((_ICON_SIZE[0] - new_size[0]) // 2, (_ICON_SIZE[1] - new_size[1]) // 2)
    canvas.paste(scaled, offset)
    if verbosity >= 1:
        print(f'  {src.name} → {_ICON_SIZE[0]}×{_ICON_SIZE[1]} PNG')
    buf = BytesIO()
    canvas.save(buf, format='PNG')
    return buf.getvalue()


def prepare_gallery_image(src: Path, verbosity: int = 0) -> bytes:
    if verbosity >= 1:
        print(f'  {src.name} → {_GALLERY_SIZE[0]}×{_GALLERY_SIZE[1]} JPEG')
    try:
        img_obj = Image.open(src)
    except Exception as e:
        raise SystemExit(f'Failed to read image {src}: {e}')
    with img_obj as img:
        out = img.convert('RGB')
        out.thumbnail(_GALLERY_SIZE, Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, format='JPEG', quality=95)
    return buf.getvalue()


def prepare_logo(src: Path, verbosity: int = 0) -> bytes:
    if verbosity >= 1:
        print(f'  {src.name} → {_LOGO_SIZE[0]}×{_LOGO_SIZE[1]} PNG')
    try:
        img_obj = Image.open(src)
    except Exception as e:
        raise SystemExit(f'Failed to read image {src}: {e}')
    with img_obj as img:
        out = img.convert('RGBA')
        out.thumbnail(_LOGO_SIZE, Image.LANCZOS)
    buf = BytesIO()
    out.save(buf, format='PNG')
    return buf.getvalue()


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
