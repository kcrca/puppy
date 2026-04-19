from pathlib import Path

from jinja2 import Environment, Undefined


class _WarnUndefined(Undefined):
    def __str__(self) -> str:
        print(f"WARNING: unknown variable '{{{{ {self._undefined_name} }}}}'")
        return f"{{{{ {self._undefined_name} }}}}"


_env = Environment(undefined=_WarnUndefined)


def substitute(text: str, config: dict, source: str = "<description>") -> str:
    return _env.from_string(text).render(config)


def find_description(puppy_dir: Path, puppy_home: Path) -> tuple[str, str] | tuple[None, None]:
    for directory in (puppy_dir, puppy_home):
        for ext in (".md", ".html", ".bbcode"):
            candidate = directory / f"description{ext}"
            if candidate.exists():
                return candidate.read_text(), str(candidate)
    return None, None
