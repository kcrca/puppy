import re
from pathlib import Path

from puppy.yaml_io import dump_puppy_yaml, load_puppy_yaml


def find_puppy_home(directory: Path) -> Path | None:
    if (directory / 'puppy' / 'puppy.yaml').exists():
        return directory / 'puppy'
    for candidate in [directory, *directory.parents]:
        if candidate.name == 'puppy' and (candidate / 'puppy.yaml').exists():
            return candidate
        if candidate == candidate.parent:
            break
    return None


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower())


def project_source(project_root: Path) -> Path:
    p = Path(project_root)
    sub = p / 'puppy'
    if (sub / 'puppy.yaml').exists():
        return sub
    return p


class Project:
    def __init__(
            self,
            project_root: Path,
            override_name: str = None,
            override_handle: str = None,
    ):
        self.root = Path(project_root)
        dir_name = self.root.name

        if override_name and override_handle:
            self.name = override_name
            self.handle = override_handle
        elif override_name:
            self.name = override_name
            self.handle = _slugify(override_name)
        elif override_handle:
            self.handle = override_handle
            self.name = (
                override_handle
                if override_handle != override_handle.lower()
                else override_handle.title()
            )
        else:
            self.handle = _slugify(dir_name)
            self.name = dir_name if dir_name != dir_name.lower() else dir_name.title()

    @classmethod
    def from_config(cls, project_root: Path, config: dict, dry_run: bool = False) -> 'Project':
        had_name = 'name' in config
        had_handle = 'handle' in config

        project = cls(
            project_root,
            override_name=config.get('name'),
            override_handle=config.get('handle'),
        )

        if not had_name:
            config['name'] = project.name
        if not had_handle:
            config['handle'] = project.handle

        if not dry_run and (not had_name or not had_handle):
            _update_yaml(
                project_source(project_root) / 'puppy.yaml',
                {
                    'name': project.name,
                    'handle': project.handle,
                },
            )

        return project

    @property
    def puppy_dir(self) -> Path:
        return project_source(self.root)


def _update_yaml(path: Path, updates: dict) -> None:
    existing = load_puppy_yaml(path)
    existing.update(updates)
    dump_puppy_yaml(existing, path)
