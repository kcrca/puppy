from pathlib import Path


_EXT_PRIORITY = {
    'curseforge': ['.html', '.md'],
    'modrinth': ['.html', '.md'],
    'planetminecraft': ['.bbcode', '.md'],
}
_DEFAULT_EXTS = ['.md']


def _extensions_for_site(site: str | None) -> list[str]:
    return _EXT_PRIORITY.get(site or '', _DEFAULT_EXTS)


class ContentDiscovery:
    def __init__(self, puppy_home: Path, project_root: Path):
        self.puppy_home = Path(puppy_home)
        self.project_root = Path(project_root)

    def find_description(
        self, *, site: str = None
    ) -> tuple[str, Path] | tuple[None, None]:
        """
        Search order (first match wins):
          1. Project site body override  ({project}/puppy/{site}/body.{ext})
          2. Project general description ({project}/puppy/description.{ext})
          3. Global general description  ({puppy_home}/description.{ext})
        """
        project_puppy = self.project_root / 'puppy'
        exts = _extensions_for_site(site)

        if site:
            for ext in exts:
                candidate = project_puppy / site / f'body{ext}'
                if candidate.exists():
                    return candidate.read_text(), candidate

        for directory in (project_puppy, self.puppy_home):
            for ext in exts:
                candidate = directory / f'description{ext}'
                if candidate.exists():
                    return candidate.read_text(), candidate

        return None, None
