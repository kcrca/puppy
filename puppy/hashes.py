import hashlib
import json
from pathlib import Path

import yaml

HASH_FILE = 'hashes.yaml'

CATEGORIES = ('file', 'images', 'data')

_LETTERS = {'f': 'file', 'i': 'images', 'd': 'data'}


def parse_content(value: str) -> set[str]:
    """Parse a -c/--content value into a set of category names.

    Accepts a comma-separated list of full names ('file,images,data'),
    a run of single letters ('fid'), or 'all'.
    """
    value = value.strip()
    if not value:
        return set()
    if value == 'all':
        return set(CATEGORIES)
    result: set[str] = set()
    if ',' in value or value in CATEGORIES:
        tokens = [t.strip() for t in value.split(',') if t.strip()]
    else:
        tokens = list(value)
    for tok in tokens:
        if tok in CATEGORIES:
            result.add(tok)
        elif tok in _LETTERS:
            result.add(_LETTERS[tok])
        else:
            raise SystemExit(
                f"puppy: error: unknown content category {tok!r} "
                f"(valid: file/f, images/i, data/d, all)"
            )
    return result


def compute(content) -> str:
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha512(content).hexdigest()


def data_hash(description: str, *parts) -> str:
    blob = description + '\x00' + '\x00'.join(
        json.dumps(p, sort_keys=True, default=str) for p in parts
    )
    return compute(blob)


def decide(category: str, content_hash: str, *, upload_set: set, use_hashes: bool, prior: dict) -> bool:
    """Whether `category` should upload this run.

    When use_hashes is false, only categories named in upload_set upload.
    When true, a named category is forced; others upload only if their hash changed.
    """
    if not use_hashes:
        return category in upload_set
    if category in upload_set:
        return True
    return prior.get(category) != content_hash


def load(puppy_dir: Path) -> dict:
    path = puppy_dir / HASH_FILE
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise SystemExit(f'{path}: {e}')


def save(puppy_dir: Path, data: dict) -> None:
    path = puppy_dir / HASH_FILE
    path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=True))
