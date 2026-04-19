from pathlib import Path


# Extension priority per site family
_HTML_SITES = {"curseforge", "modrinth"}
_BBCODE_SITES = {"pmc"}


def _extensions_for_site(site: str | None) -> list[str]:
    if site in _HTML_SITES:
        return [".html", ".md"]
    if site in _BBCODE_SITES:
        return [".bbcode", ".md"]
    return [".md"]


class ContentDiscovery:
    def __init__(self, puppy_home: Path, project_root: Path):
        self.puppy_home = Path(puppy_home)
        self.project_root = Path(project_root)

    def find_fragment(self, name: str, *, site: str | None = None) -> tuple[str, Path]:
        """
        Search order (first match wins):
          1. YAML strings block  — handled upstream; not searched here
          2. Project site file   (project/puppy/<site>/<name>)
          3. Project general     (project/puppy/<name>)
          4. Global site file    (puppy_home/<site>/<name>)
          5. Global general      (puppy_home/<name>)
        Returns (content, path).
        """
        project_puppy = self.project_root / "puppy"
        extensions = _extensions_for_site(site)

        search_dirs: list[Path] = []
        if site:
            search_dirs.append(project_puppy / site)
        search_dirs.append(project_puppy)
        if site:
            search_dirs.append(self.puppy_home / site)
        search_dirs.append(self.puppy_home)

        for directory in search_dirs:
            for ext in extensions:
                candidate = directory / f"{name}{ext}"
                if candidate.exists():
                    return candidate.read_text(), candidate

        raise FileNotFoundError(f"Fragment '{name}' not found for site '{site}'")
