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

        site_dir = (project_puppy / site.name) if site else None
        dirs = ([site_dir] if site_dir else []) + [project_puppy, self.puppy_home]

        for directory in dirs:
            for ext in exts:
                candidate = directory / f'{name}{ext}'
                if candidate.exists():
                    if directory == site_dir:
                        for shadowed_ext in exts:
                            if shadowed_ext != ext:
                                shadowed = directory / f'{name}{shadowed_ext}'
                                if shadowed.exists():
                                    print(f'WARNING: {shadowed} is shadowed by {candidate} and will never be used')
                    return candidate.read_text(), candidate

        return None, None

    def find_description(self, *, site: Site = None) -> tuple[str, Path] | tuple[None, None]:
        return self.find('description', site=site)
