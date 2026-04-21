import markdown as _md
from jinja2 import Environment, Undefined

from puppy.transformers import PMCTransformer


class _WarnUndefined(Undefined):
    def __str__(self) -> str:
        print(f"WARNING: unknown variable '{{{{ {self._undefined_name} }}}}'")
        return f'{{{{ {self._undefined_name} }}}}'


_env = Environment(undefined=_WarnUndefined)

DEFAULT_SHIELD_TAGS = ['u']


def md_to_html(text: str) -> str:
    return _md.markdown(text, extensions=['extra'])


_pmc = PMCTransformer()


def md_to_bbcode(text: str) -> str:
    return _pmc.md_to_bbcode(text)


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
