import shutil
from pathlib import Path

import yaml

from puppy.sites import SiteVisitor


REQUIRED_TOOLS = ['git', 'node', 'npm']

_AUTH_SHAPE = {
    'curseforge': {'token', 'cookie'},
    'modrinth': None,
    'planetminecraft': None,
}


def check_preflight() -> None:
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        raise SystemExit(f'Missing required tools: {", ".join(missing)}')


def check_auth(puppy_home: Path, site: str = None) -> dict:
    gitignore = puppy_home / '.gitignore'
    auth_file = puppy_home / 'auth.yaml'

    if not auth_file.exists():
        raise SystemExit(f'auth.yaml not found in {puppy_home}')

    if not gitignore.exists() or 'auth.yaml' not in gitignore.read_text().splitlines():
        raise SystemExit(f'auth.yaml must be listed in {gitignore} — refusing to run')

    auth = yaml.safe_load(auth_file.read_text())
    if not auth:
        raise SystemExit(f'auth.yaml is empty — add your site credentials')
    visitor = SiteVisitor(site)
    unchanged = [s.name for s in visitor if _has_placeholders(auth.get(s.name))]
    if unchanged:
        raise SystemExit(
            f'auth.yaml credentials unchanged for: {", ".join(unchanged)}'
        )
    for s in visitor:
        required_keys = _AUTH_SHAPE.get(s.name)
        if required_keys:
            entry = auth.get(s.name) or {}
            missing = required_keys - entry.keys()
            if missing:
                raise SystemExit(
                    f'auth.yaml [{s.name}] missing required keys: {", ".join(sorted(missing))}'
                )
    return auth


def _has_placeholders(value) -> bool:
    if isinstance(value, str):
        return 'YOUR_' in value
    if isinstance(value, dict):
        return any(_has_placeholders(v) for v in value.values())
    return False
