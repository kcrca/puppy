import markdown as _md
from jinja2 import Environment, Undefined, UndefinedError

from puppy.transformers import PMCTransformer


class _ErrorUndefined(Undefined):
    """Raises on string rendering; stays falsy for {% if %} tests."""
    def __str__(self) -> str:
        raise UndefinedError(f"unknown variable '{self._undefined_name}'")

    def __iter__(self):
        raise UndefinedError(f"unknown variable '{self._undefined_name}'")


_env = Environment(undefined=_ErrorUndefined)

DEFAULT_SHIELD_TAGS = ['u']


class _SiteProxy:
    """Wraps a {site_name: {attr: val}} dict.

    Attribute access for a known site name returns that site's sub-dict unchanged.
    Any other attribute falls back to the current site's sub-dict, or '' if absent.
    """

    def __init__(self, data: dict, current_site: str):
        self._data = data
        self._site = current_site

    def _resolve(self, key: str):
        if key in self._data:
            return self._data[key]
        return self._data.get(self._site, {}).get(key, '')

    def __getattr__(self, name: str):
        if name.startswith('_'):
            raise AttributeError(name)
        return self._resolve(name)

    def __getitem__(self, key: str):
        return self._resolve(key)


def md_to_html(text: str) -> str:
    return _md.markdown(text, extensions=['extra'])


_pmc = PMCTransformer()


def md_to_bbcode(text: str) -> str:
    return _pmc.md_to_bbcode(text)


def _resolve_config_strings(ctx: dict) -> dict:
    while True:
        resolved = {}
        for k, v in ctx.items():
            if isinstance(v, str) and '{{' in v:
                resolved[k] = _env.from_string(v).render(ctx)
            else:
                resolved[k] = v
        if resolved == ctx:
            return ctx
        ctx = resolved


def render(text: str, config: dict, source: str = '<description>', *, site=None) -> str:
    tags = config.get('md_html_tags', DEFAULT_SHIELD_TAGS)
    ctx = config
    if site and 'projects' in config:
        ctx = dict(config)
        ctx['projects'] = {
            pack: _SiteProxy(proj, site.name)
            for pack, proj in config['projects'].items()
        }
    ctx = _resolve_config_strings(ctx)
    result = _env.from_string(text).render(ctx)
    if site:
        open_map, close_map = site.shield_tags(tags)
        for tag, native in open_map.items():
            result = result.replace(f'<{tag}>', native)
        for tag, native in close_map.items():
            result = result.replace(f'</{tag}>', native)
    return result
