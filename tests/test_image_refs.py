"""Tests for {{ images.name }} and {{ img('name') }} in descriptions."""

from puppy.renderer import render
from puppy.sites import CURSEFORGE, MODRINTH, PMC


URLS = {'banner': 'https://cdn.example.com/banner.jpg', 'screenshot': 'https://cdn.example.com/ss.jpg'}


def test_images_attr_access():
    result = render('{{ images.banner }}', {}, image_urls=URLS)
    assert result == 'https://cdn.example.com/banner.jpg'


def test_images_item_access():
    result = render("{{ images['banner'] }}", {}, image_urls=URLS)
    assert result == 'https://cdn.example.com/banner.jpg'


def test_images_missing_key_returns_empty():
    result = render('{{ images.nonexistent }}', {}, image_urls=URLS)
    assert result == ''


def test_images_no_urls_provided():
    result = render('{{ images.banner }}', {})
    assert result == ''


def test_img_cf():
    result = render("{{ img('banner') }}", {}, site=CURSEFORGE, image_urls=URLS)
    assert result == '<img src="https://cdn.example.com/banner.jpg" width="600" alt="banner"><br>'


def test_img_mr():
    result = render("{{ img('banner') }}", {}, site=MODRINTH, image_urls=URLS)
    assert result == '<img src="https://cdn.example.com/banner.jpg" width="600" alt="banner"><br><br>'


def test_img_pmc():
    result = render("{{ img('banner') }}", {}, site=PMC, image_urls=URLS)
    assert result == '[img]https://cdn.example.com/banner.jpg[/img]'


def test_img_pmc_md_source():
    result = render("{{ img('banner') }}", {}, source='desc.md', site=PMC, image_urls=URLS)
    assert result == '![banner](https://cdn.example.com/banner.jpg)'


def test_img_pmc_md_source_roundtrip():
    from puppy.renderer import md_to_bbcode
    rendered = render("{{ img('banner') }}", {}, source='desc.md', site=PMC, image_urls=URLS)
    bbcode = md_to_bbcode(rendered)
    assert '[img=banner]https://cdn.example.com/banner.jpg[/img]' in bbcode


def test_img_missing_key_returns_empty():
    result = render("{{ img('nope') }}", {}, site=MODRINTH, image_urls=URLS)
    assert result == ''


def test_img_no_urls_provided_returns_empty():
    result = render("{{ img('banner') }}", {}, site=CURSEFORGE)
    assert result == ''


def test_img_tag_cf_directly():
    tag = CURSEFORGE.img_tag('https://cdn.example.com/img.jpg', 'photo')
    assert tag == '<img src="https://cdn.example.com/img.jpg" width="600" alt="photo"><br>'


def test_img_tag_mr_directly():
    tag = MODRINTH.img_tag('https://cdn.example.com/img.jpg', 'photo')
    assert tag == '<img src="https://cdn.example.com/img.jpg" width="600" alt="photo"><br><br>'


def test_img_tag_pmc_directly():
    tag = PMC.img_tag('https://cdn.example.com/img.jpg', 'photo')
    assert tag == '[img]https://cdn.example.com/img.jpg[/img]'


def test_images_coexist_with_other_vars():
    config = {'version': '1.0', 'name': 'MyPack'}
    result = render('{{ name }} v{{ version }}: {{ images.banner }}', config, image_urls=URLS)
    assert result == 'MyPack v1.0: https://cdn.example.com/banner.jpg'


def test_images_in_conditional():
    result = render(
        '{% if images.banner %}has banner{% else %}no banner{% endif %}',
        {},
        image_urls=URLS,
    )
    assert result == 'has banner'


def test_images_absent_in_conditional():
    result = render(
        '{% if images.banner %}has banner{% else %}no banner{% endif %}',
        {},
    )
    assert result == 'no banner'
