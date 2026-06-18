from io import BytesIO
from pathlib import Path

from PIL import Image

from puppy.images import prepare_gallery_image, prepare_icon


def _make_image(tmp_path: Path, size=(800, 600), mode='RGB', fmt='PNG') -> Path:
    p = tmp_path / f'test.{fmt.lower()}'
    Image.new(mode, size, color='blue').save(p, format=fmt)
    return p


def test_prepare_icon_size(tmp_path):
    src = _make_image(tmp_path, size=(200, 200))
    data = prepare_icon(src)
    with Image.open(BytesIO(data)) as img:
        assert img.size == (512, 512)
        assert img.format == 'PNG'


def test_prepare_icon_non_square(tmp_path, capsys):
    src = _make_image(tmp_path, size=(300, 100))
    data = prepare_icon(src)
    with Image.open(BytesIO(data)) as img:
        assert img.size == (512, 512)
        assert img.mode == 'RGBA'
        # top-left corner should be transparent (padding area)
        assert img.getpixel((0, 0))[3] == 0
    assert 'not square' in capsys.readouterr().out


def test_prepare_gallery_image_fits(tmp_path):
    src = _make_image(tmp_path, size=(3000, 2000))
    data = prepare_gallery_image(src)
    with Image.open(BytesIO(data)) as img:
        assert img.format == 'JPEG'
        assert img.size[0] <= 1920
        assert img.size[1] <= 1080


def test_prepare_gallery_image_no_upscale(tmp_path):
    src = _make_image(tmp_path, size=(320, 240))
    data = prepare_gallery_image(src)
    with Image.open(BytesIO(data)) as img:
        assert img.size == (320, 240)
