from pathlib import Path

import yaml


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
            self.pack = override_name.lower()
        elif override_pack:
            self.pack = override_pack
            self.name = (
                override_pack
                if override_pack != override_pack.lower()
                else override_pack.title()
            )
        else:
            self.pack = dir_name.lower()
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
                project_root / 'puppy' / 'puppy.yaml',
                {
                    'name': project.name,
                    'pack': project.pack,
                },
            )

        return project

    @property
    def puppy_dir(self) -> Path:
        return self.root / 'puppy'


def _update_yaml(path: Path, updates: dict) -> None:
    existing = {}
    if path.exists():
        with path.open() as f:
            existing = yaml.safe_load(f) or {}
    existing.update(updates)
    with path.open('w') as f:
        yaml.dump(
            existing, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
