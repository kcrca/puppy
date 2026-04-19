from pathlib import Path


class Project:
    def __init__(self, project_root: Path, override_name: str | None = None, override_pack: str | None = None):
        self.root = Path(project_root)
        dir_name = self.root.name

        if override_pack:
            self.pack = override_pack
        else:
            self.pack = dir_name.lower()

        if override_name:
            self.name = override_name
        elif dir_name == dir_name.lower():
            self.name = dir_name.title()
        else:
            self.name = dir_name

    @property
    def puppy_dir(self) -> Path:
        return self.root / "puppy"
