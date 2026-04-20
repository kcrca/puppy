from jinja2 import Environment, Undefined


class _WarnUndefined(Undefined):
    def __str__(self) -> str:
        print(f"WARNING: unknown variable '{{{{ {self._undefined_name} }}}}'")
        return f"{{{{ {self._undefined_name} }}}}"


_env = Environment(undefined=_WarnUndefined)


def render(text: str, config: dict, source: str = "<description>") -> str:
    return _env.from_string(text).render(config)
