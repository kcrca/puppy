import re
from pathlib import Path

import markdown as _md
from jinja2 import Environment, Undefined, UndefinedError

from puppy.transformers import PMCTransformer


class _ErrorUndefined(Undefined):
    """Raises on string rendering; stays falsy for {% if %} tests."""
    def __str__(self) -> str:
        raise UndefinedError(f"unknown variable '{self._undefined_name}'")

    def __iter__(self):
        raise UndefinedError(f"unknown variable '{self._undefined_name}'")


def _read_file(path: str) -> str:
    return Path(path).read_text()


_env = Environment(undefined=_ErrorUndefined)
_env.globals['read'] = _read_file

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


_SIMPLE_VAR = re.compile(r'\{\{\s*([a-zA-Z_]\w*)\s*\}\}')


def _collect_undefined(texts: list[str], ctx: dict) -> set[str]:
    names = set()
    for t in texts:
        if not isinstance(t, str):
            continue
        for m in _SIMPLE_VAR.finditer(t):
            if m.group(1) not in ctx:
                names.add(m.group(1))
    return names


def _pre_populate_files(text: str, ctx: dict, discovery) -> dict:
    """Add file-cascade inclusions for any {{ name }} not yet in ctx."""
    from puppy.searcher import ContentDiscovery  # avoid import cycle at module level
    site = ctx.get('_site')
    pending = {text}
    while True:
        names = _collect_undefined(list(pending) + list(ctx.values() if ctx else []), ctx)
        if not names:
            break
        added = False
        for name in names:
            content, _ = discovery.find(name, site=site)
            if content is not None:
                ctx[name] = content
                pending.add(content)
                added = True
        if not added:
            break
    return ctx


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
    from puppy.searcher import ContentDiscovery
    tags = config.get('md_html_tags', DEFAULT_SHIELD_TAGS)
    ctx = dict(config)
    if site and 'projects' in config:
        ctx['projects'] = {
            pack: _SiteProxy(proj, site.name)
            for pack, proj in config['projects'].items()
        }
    if ctx.get('puppy') and ctx.get('project'):
        ctx['_site'] = site
        discovery = ContentDiscovery(ctx['puppy'], ctx['project'])
        ctx = _pre_populate_files(text, ctx, discovery)
        del ctx['_site']
    ctx = _resolve_config_strings(ctx)
    result = _env.from_string(text).render(ctx)
    if site:
        open_map, close_map = site.shield_tags(tags)
        for tag, native in open_map.items():
            result = result.replace(f'<{tag}>', native)
        for tag, native in close_map.items():
            result = result.replace(f'</{tag}>', native)
    return result
