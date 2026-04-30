from pathlib import Path

from ruamel.yaml import YAML


def _rt() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    return y


def load_puppy_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return _rt().load(path) or {}


def dump_puppy_yaml(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        _rt().dump(data, f)
