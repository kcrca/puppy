from puppy.preview import _to_html
from puppy.renderer import md_to_bbcode


def test_bbcode_paragraphs_use_p_tags_not_br():
    bbcode = md_to_bbcode('First paragraph.\n\nSecond paragraph.\n\nThird paragraph.')
    result = _to_html(bbcode, '.bbcode')
    assert '<br />' not in result
    assert result.count('<p>') == 3
    assert 'First paragraph.' in result
    assert 'Second paragraph.' in result
    assert 'Third paragraph.' in result


def test_bbcode_no_leading_br_after_heading():
    bbcode = md_to_bbcode('# My Title\n\nFirst paragraph.')
    result = _to_html(bbcode, '.bbcode')
    assert '<br />' not in result
    assert '<h1>My Title</h1>' in result
    assert result.index('<h1>') < result.index('<p>First paragraph.</p>')
