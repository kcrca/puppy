from jinja2 import Environment, Undefined


class _WarnUndefined(Undefined):
    def __str__(self) -> str:
        print(f"WARNING: unknown variable '{{{{ {self._undefined_name} }}}}'")
        return f"{{{{ {self._undefined_name} }}}}"


_env = Environment(undefined=_WarnUndefined)

DEFAULT_SHIELD_TAGS = ["u"]

_PMC_TAG = {tag: f"[{tag}]" for tag in DEFAULT_SHIELD_TAGS}
_PMC_CLOSE_TAG = {tag: f"[/{tag}]" for tag in DEFAULT_SHIELD_TAGS}


def _site_tag_maps(site: str, tags: list[str]) -> tuple[dict, dict]:
    """Return (open_map, close_map) translating HTML tags to site-native equivalents."""
    if site == "planetminecraft":
        return {t: f"[{t}]" for t in tags}, {t: f"[/{t}]" for t in tags}
    return {}, {}


def render(text: str, config: dict, source: str = "<description>", *, site: str | None = None) -> str:
    tags = config.get("md_html_tags", DEFAULT_SHIELD_TAGS)
    result = _env.from_string(text).render(config)
    if site:
        open_map, close_map = _site_tag_maps(site, tags)
        for tag, native in open_map.items():
            result = result.replace(f"<{tag}>", native)
        for tag, native in close_map.items():
            result = result.replace(f"</{tag}>", native)
    return result
