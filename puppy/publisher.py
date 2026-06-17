from pathlib import Path

from puppy.artifacts import ArtifactFinder
from puppy.core import Project


def _resolve_zip(config: dict, puppy_dir: Path, version: str, project: Project) -> Path:
    explicit = config.get('file')
    if explicit:
        p = Path(explicit) if Path(explicit).is_absolute() else (puppy_dir / explicit).resolve()
        if not p.exists():
            raise SystemExit(f'Zip not found: {p}')
        return p
    try:
        return ArtifactFinder(puppy_dir).find(project=project.handle, version=version)
    except FileNotFoundError as e:
        raise SystemExit(str(e))
