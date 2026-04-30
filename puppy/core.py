import re
from pathlib import Path

from puppy.yaml_io import dump_puppy_yaml, load_puppy_yaml


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower())


def project_source(project_root: Path) -> Path:
    return Path(project_root)


class Project:
    def __init__(
            self,
            project_root: Path,
            override_name: str = None,
            override_pack: str = None,
    ):
        self.root = Path(project_root)
        dir_name = self.root.name

        if override_name and override_pack:
            self.name = override_name
            self.pack = override_pack
        elif override_name:
            self.name = override_name
            self.pack = _slugify(override_name)
        elif override_pack:
            self.pack = override_pack
            self.name = (
                override_pack
                if override_pack != override_pack.lower()
                else override_pack.title()
            )
        else:
            self.pack = _slugify(dir_name)
            self.name = dir_name if dir_name != dir_name.lower() else dir_name.title()

    @classmethod
    def from_config(cls, project_root: Path, config: dict) -> 'Project':
        had_name = 'name' in config
        had_pack = 'pack' in config

        project = cls(
            project_root,
            override_name=config.get('name'),
            override_pack=config.get('pack'),
        )

        if not had_name or not had_pack:
            _update_yaml(
                project_source(project_root) / 'puppy.yaml',
                {
                    'name': project.name,
                    'pack': project.pack,
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
