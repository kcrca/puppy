from pathlib import Path


class Project:
    def __init__(self, project_root: Path, override_name: str | None = None, override_pack: str | None = None):
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
            self.name = override_pack if override_pack != override_pack.lower() else override_pack.title()
        else:
            self.pack = dir_name.lower()
            self.name = dir_name if dir_name != dir_name.lower() else dir_name.title()

    @property
    def puppy_dir(self) -> Path:
        return self.root / "puppy"
