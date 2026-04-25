from pathlib import Path

from puppy.core import project_source
from puppy.sites import Site

_DEFAULT_EXTS = ['.md']


class ContentDiscovery:
    def __init__(self, puppy_home: Path, project_root: Path):
        self.puppy_home = Path(puppy_home)
        self.project_root = Path(project_root)

    def find(
        self, name: str, *, site: Site = None
    ) -> tuple[str, Path] | tuple[None, None]:
        """Search cascade for {name}.{ext} (project-site → project → global)."""
        project_puppy = project_source(self.project_root)
        exts = site.desc_exts if site else _DEFAULT_EXTS

        if site:
            for ext in exts:
                candidate = project_puppy / site.name / f'{name}{ext}'
                if candidate.exists():
                    return candidate.read_text(), candidate

        for directory in (project_puppy, self.puppy_home):
            for ext in exts:
                candidate = directory / f'{name}{ext}'
                if candidate.exists():
                    return candidate.read_text(), candidate

        return None, None

    def find_description(self, *, site: Site = None) -> tuple[str, Path] | tuple[None, None]:
        return self.find('description', site=site)
