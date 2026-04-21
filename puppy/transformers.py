import re

import bbcode
import mistune
from md2bbcode.renderers.bbcode import BBCodeRenderer

# PMC wraps outbound links in a tracking path; strip it back to the raw URL.
_PMC_LINK_RE = re.compile(r'/account/manage/texture-packs/\d+/([^\]]+)')


class _MdToBBCode(BBCodeRenderer):
    """Mistune renderer: Markdown → PMC BBCode dialect."""

    def heading(self, text: str, level: int, **attrs) -> str:
        return f'[h{level}]{text}[/h{level}]\n'

    def list_item(self, text: str) -> str:
        # PMC requires explicit [/*] terminators on list items
        return f'[*]{text.strip()}[/*]\n'

    def softbreak(self) -> str:
        return ' '

    def image(self, text: str, url: str, title=None) -> str:
        # PMC uses [img=alt] rather than a separate alt attribute
        if text:
            return f'[img={text}]{url}[/img]'
        return f'[img]{url}[/img]'


def _img_fmt(tag_name, value, options, parent, context):
    alt = options.get('img', '')
    src = value.strip()
    if alt:
        return f'<img src="{src}" alt="{alt}" style="max-width:100%">'
    return f'<img src="{src}" style="max-width:100%">'


def _heading_fmt(tag_name, value, options, parent, context):
    return f'<{tag_name}>{value}</{tag_name}>'


def _spoiler_fmt(tag_name, value, options, parent, context):
    title = options.get('spoiler', 'Show')
    return f'<details><summary>{title}</summary>{value}</details>'


def _size_fmt(tag_name, value, options, parent, context):
    size = options.get('size', '')
    return f'<span style="font-size:{size}">{value}</span>'


def _bgcolor_fmt(tag_name, value, options, parent, context):
    color = options.get('bgcolor', '')
    return f'<span style="background-color:{color}">{value}</span>'


def _style_fmt(tag_name, value, options, parent, context):
    # [style b color=#xxx]text[/style] — PMC composite inline style tag
    css = []
    if 'color' in options:
        css.append(f'color:{options["color"]}')
    inner = value
    if 'b' in options:
        inner = f'<strong>{inner}</strong>'
    if 'i' in options:
        inner = f'<em>{inner}</em>'
    if css:
        return f'<span style="{";".join(css)}">{inner}</span>'
    return inner


def _td_fmt(tag_name, value, options, parent, context):
    width = options.get('width', '')
    if width:
        return f'<td width="{width}">{value}</td>'
    return f'<td>{value}</td>'


def _build_bb_parser() -> bbcode.Parser:
    parser = bbcode.Parser(escape_html=True, replace_links=False, replace_cosmetic=False)
    parser.add_formatter('img', _img_fmt, replace_links=False, replace_cosmetic=False)
    for n in range(1, 7):
        parser.add_formatter(f'h{n}', _heading_fmt)
    parser.add_formatter('spoiler', _spoiler_fmt, has_argument=True)
    parser.add_formatter('size', _size_fmt, has_argument=True)
    parser.add_formatter('bgcolor', _bgcolor_fmt, has_argument=True)
    parser.add_formatter('style', _style_fmt)
    # [hr] is a void element; standalone=True prevents it from consuming subsequent content
    parser.add_formatter('hr', lambda *a, **k: '<hr>', standalone=True)
    parser.add_formatter('table', lambda *a, **k: f'<table>{a[1]}</table>')
    parser.add_formatter('tbody', lambda *a, **k: f'<tbody>{a[1]}</tbody>')
    parser.add_formatter('thead', lambda *a, **k: f'<thead>{a[1]}</thead>')
    parser.add_formatter('tr', lambda *a, **k: f'<tr>{a[1]}</tr>')
    parser.add_formatter('td', _td_fmt)
    parser.add_formatter('th', lambda *a, **k: f'<th>{a[1]}</th>')
    return parser


class PMCTransformer:
    """Converts between Markdown, PMC BBCode, and preview HTML."""

    def __init__(self):
        self._md_parser = mistune.create_markdown(renderer=_MdToBBCode(domain=''))
        self._bb_parser = _build_bb_parser()

    def md_to_bbcode(self, text: str) -> str:
        return self._md_parser(text)

    def bbcode_to_html(self, text: str) -> str:
        text = _PMC_LINK_RE.sub(r'https://\1', text)
        return self._bb_parser.format(text)
