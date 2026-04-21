import re

import markdown as _md
import mistune
from md2bbcode.main import convert_markdown_to_bbcode
from md2bbcode.renderers.bbcode import BBCodeRenderer
from jinja2 import Environment, Undefined


class _WarnUndefined(Undefined):
    def __str__(self) -> str:
        print(f"WARNING: unknown variable '{{{{ {self._undefined_name} }}}}'")
        return f'{{{{ {self._undefined_name} }}}}'


_env = Environment(undefined=_WarnUndefined)

DEFAULT_SHIELD_TAGS = ['u']


def md_to_html(text: str) -> str:
    return _md.markdown(text, extensions=['extra'])


class _PMCRenderer(BBCodeRenderer):
    def image(self, text: str, url: str, title=None) -> str:
        return f'[img]{url}[/img]'

    def heading(self, text: str, level: int, **attrs) -> str:
        return f'[h{level}]{text}[/h{level}]\n'


_pmc_parser = mistune.create_markdown(renderer=_PMCRenderer(domain=''))


def md_to_bbcode(text: str) -> str:
    # Normalize soft-wrapped lines (single newlines) to spaces before converting
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    return _pmc_parser(text)


def render(text: str, config: dict, source: str = '<description>', *, site=None) -> str:
    tags = config.get('md_html_tags', DEFAULT_SHIELD_TAGS)
    result = _env.from_string(text).render(config)
    if site:
        open_map, close_map = site.shield_tags(tags)
        for tag, native in open_map.items():
            result = result.replace(f'<{tag}>', native)
        for tag, native in close_map.items():
            result = result.replace(f'</{tag}>', native)
    return result
