from pathlib import Path


_EXT_PRIORITY = {
    "curseforge": [".html", ".md"],
    "modrinth": [".html", ".md"],
    "planetminecraft": [".bbcode", ".md"],
}
_DEFAULT_EXTS = [".md"]


def _extensions_for_site(site: str | None) -> list[str]:
    return _EXT_PRIORITY.get(site or "", _DEFAULT_EXTS)


class ContentDiscovery:
    def __init__(self, puppy_home: Path, project_root: Path):
        self.puppy_home = Path(puppy_home)
        self.project_root = Path(project_root)

    def find_fragment(self, name: str, *, site: str | None = None) -> tuple[str, Path] | tuple[None, None]:
        """
        Search order (first match wins):
          1. Project site dir   ({project}/puppy/{site}/{name}.{ext})
          2. Project general    ({project}/puppy/{name}.{ext})
          3. Global site dir    ({puppy_home}/{site}/{name}.{ext})
          4. Global general     ({puppy_home}/{name}.{ext})
        Extension priority per site: .html/.md for CF/Modrinth; .bbcode/.md for PMC; .md otherwise.
        """
        project_puppy = self.project_root / "puppy"
        exts = _extensions_for_site(site)

        dirs: list[Path] = []
        if site:
            dirs.append(project_puppy / site)
        dirs.append(project_puppy)
        if site:
            dirs.append(self.puppy_home / site)
        dirs.append(self.puppy_home)

        for d in dirs:
            for ext in exts:
                candidate = d / f"{name}{ext}"
                if candidate.exists():
                    return candidate.read_text(), candidate

        return None, None

    def find_description(self, *, site: str | None = None) -> tuple[str, Path] | tuple[None, None]:
        """
        Find description body. Checks site-specific 'body' override first,
        then falls back to general 'description' at project and global levels.
        """
        project_puppy = self.project_root / "puppy"
        exts = _extensions_for_site(site)

        if site:
            for ext in exts:
                candidate = project_puppy / site / f"body{ext}"
                if candidate.exists():
                    return candidate.read_text(), candidate

        for directory in (project_puppy, self.puppy_home):
            for ext in exts:
                candidate = directory / f"description{ext}"
                if candidate.exists():
                    return candidate.read_text(), candidate

        return None, None
