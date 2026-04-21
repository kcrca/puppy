import pytest
from puppy.transformers import PMCTransformer

@pytest.fixture
def transformer():
    return PMCTransformer()

def test_md_to_bbcode_headers(transformer):
    """Verify Markdown headers map to PMC h-tags."""
    md = "# Large Header\n## Medium Header"
    bb = transformer.md_to_bbcode(md)
    assert "[h1]Large Header[/h1]" in bb
    assert "[h2]Medium Header[/h2]" in bb

def test_md_to_bbcode_lists(transformer):
    """Verify lists include the PMC-required [/*] terminator."""
    md = "* Item 1\n* Item 2"
    bb = transformer.md_to_bbcode(md)
    assert "[*]Item 1[/*]" in bb
    assert "[*]Item 2[/*]" in bb
    assert "[list]" in bb and "[/list]" in bb

def test_bbcode_to_html_link_cleaning(transformer):
    """Verify PMC internal tracking links are stripped to raw URLs."""
    dirty_url = "[url=/account/manage/texture-packs/6136773/google.com]Google[/url]"
    html = transformer.bbcode_to_html(dirty_url)
    assert 'href="https://google.com"' in html
    assert 'Google</a>' in html

def test_bbcode_to_html_nesting(transformer):
    """Verify interlocking tags are handled by the tree parser."""
    # The bbcode library should fix this 'interlocking' mess into valid HTML
    bad_nesting = "[b]bold [i]italic[/b][/i]"
    html = transformer.bbcode_to_html(bad_nesting)
    # Valid HTML requires <strong><em>...</em></strong> or <em><strong>...</strong></em>
    assert "<strong>bold <em>italic</em></strong>" in html or "<em><strong>bold </strong>italic</em>" in html

def test_complex_table_roundtrip(transformer):
    """Ensure a table with formatting inside renders correctly in HTML."""
    bb = "[table][tbody][tr][td][b]Cell Content[/b][/td][/tr][/tbody][/table]"
    html = transformer.bbcode_to_html(bb)
    assert "<table" in html
    assert "<strong>Cell Content</strong>" in html
    assert "</td>" in html

def test_spoiler_rendering(transformer):
    """Verify [spoiler=Title] becomes a details/summary block."""
    bb = "[spoiler=View More]Hidden Secrets[/spoiler]"
    html = transformer.bbcode_to_html(bb)
    assert "<details" in html
    assert "<summary" in html
    assert "View More" in html
    assert "Hidden Secrets" in html

def test_image_alt_text(transformer):
    """Verify images handle the alt-text parameter correctly."""
    md = "![Description](https://example.com/img.png)"
    bb = transformer.md_to_bbcode(md)
    assert "[img=Description]https://example.com/img.png[/img]" in bb

def test_hr_does_not_swallow_content(transformer):
    """Bare [hr] must not consume subsequent text."""
    html = transformer.bbcode_to_html('before[hr]after')
    assert '<hr>' in html
    assert 'after' in html

def test_size_tag(transformer):
    html = transformer.bbcode_to_html('[size=24px]big text[/size]')
    assert 'font-size:24px' in html
    assert 'big text' in html

def test_bgcolor_tag(transformer):
    html = transformer.bbcode_to_html('[bgcolor=#ff0000]highlighted[/bgcolor]')
    assert 'background-color:#ff0000' in html
    assert 'highlighted' in html

def test_style_tag_bold_color(transformer):
    html = transformer.bbcode_to_html('[style b color=#0000ff]styled[/style]')
    assert '<strong>' in html
    assert 'color:#0000ff' in html
    assert 'styled' in html

def test_td_width_attribute(transformer):
    html = transformer.bbcode_to_html('[table][tr][td width=25%]cell[/td][/tr][/table]')
    assert 'width="25%"' in html
    assert 'cell' in html

def test_h3_heading(transformer):
    html = transformer.bbcode_to_html('[h3]Sub-heading[/h3]')
    assert '<h3>Sub-heading</h3>' in html

def test_color_tag(transformer):
    html = transformer.bbcode_to_html('[color=#00ffff]cyan[/color]')
    assert 'color:#00ffff' in html
    assert 'cyan' in html

def test_underline_tag(transformer):
    html = transformer.bbcode_to_html('[u]underline[/u]')
    assert '<u>underline</u>' in html

def test_italic_tag(transformer):
    html = transformer.bbcode_to_html('[i]italic[/i]')
    assert '<em>italic</em>' in html

def test_quote_tag(transformer):
    html = transformer.bbcode_to_html('[quote]quoted text[/quote]')
    assert '<blockquote>' in html
    assert 'quoted text' in html

def test_code_tag(transformer):
    html = transformer.bbcode_to_html('[code]some_code()[/code]')
    assert '<code>' in html
    assert 'some_code()' in html

def test_md_to_bbcode_blockquote(transformer):
    bb = transformer.md_to_bbcode('> quoted text')
    assert 'quoted text' in bb
    assert 'QUOTE' in bb or 'quote' in bb

def test_md_to_bbcode_fenced_code(transformer):
    bb = transformer.md_to_bbcode('```\nsome code\n```')
    assert 'some code' in bb
    assert 'CODE' in bb or 'code' in bb

def test_md_to_bbcode_codespan(transformer):
    bb = transformer.md_to_bbcode('use `func()` here')
    assert 'func()' in bb
    assert 'icode' in bb or 'code' in bb

def test_blockquote_roundtrip(transformer):
    """Blockquotes produced by md_to_bbcode must survive bbcode_to_html."""
    bb = transformer.md_to_bbcode('> a quote')
    html = transformer.bbcode_to_html(bb)
    assert 'a quote' in html