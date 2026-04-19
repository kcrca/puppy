import re

from jinja2 import Environment, Undefined


class _WarnUndefined(Undefined):
    def __str__(self) -> str:
        print(f"WARNING: unknown variable '{{{{ {self._undefined_name} }}}}'")
        return f"{{{{ {self._undefined_name} }}}}"


_env = Environment(undefined=_WarnUndefined)


def _expand_snippets(text: str, discovery, site: str | None) -> str:
    def replace(m: re.Match) -> str:
        name = m.group(1).strip()
        content, _ = discovery.find_fragment(name, site=site)
        if content is not None:
            return content
        print(f"WARNING: snippet '{name}' not found")
        return m.group(0)
    return re.sub(r'\{\{\s*snippet:(\w+)\s*\}\}', replace, text)


def render(text: str, config: dict, *, discovery=None, site: str | None = None, source: str = "<description>") -> str:
    if discovery:
        text = _expand_snippets(text, discovery, site)
    return _env.from_string(text).render(config)


def substitute(text: str, config: dict, source: str = "<description>") -> str:
    return render(text, config, source=source)
