from pathlib import Path


_AUTH_YAML = """\
# auth.yaml — API credentials. NEVER commit this file.
# Listed in .gitignore — puppy will refuse to run if it is not.

curseforge:
  token: YOUR_CURSEFORGE_API_TOKEN
  cookie: CobaltSession=YOUR_COBALT_SESSION_COOKIE

modrinth: YOUR_MODRINTH_TOKEN

planetminecraft: pmc_autologin=YOUR_PMC_AUTOLOGIN_COOKIE
"""

_GITIGNORE = "auth.yaml\n"

_DESCRIPTION_MD = """\
<!-- Add your pack description here. Jinja2 variables from puppy.yaml are available,
     e.g. {{ version }}, {{ name }}. Conditionals: {% if key %}...{% endif %} -->
"""

_SITE_TEMPLATES = {
    "curseforge": ("description.html", "<!-- CurseForge description (HTML) -->\n"),
    "modrinth": ("description.md", "<!-- Modrinth description (Markdown) -->\n"),
    "planetminecraft": ("description.bbcode", "[b]Planet Minecraft description (BBCode)[/b]\n"),
}


def _derive_identity(directory: Path) -> tuple[str, str]:
    dir_name = directory.name
    if dir_name == dir_name.lower():
        return dir_name.title(), dir_name
    return dir_name, dir_name.lower()


def _global_puppy_yaml(name: str) -> str:
    return f"""\
# Global puppy.yaml — defaults that apply to all projects.
# Place site-specific overrides in puppy/[sitename]/puppy.yaml.

projects:
  - {name}
"""


def _project_puppy_yaml(name: str, pack: str) -> str:
    return f"""\
# puppy.yaml — project configuration for {name}.

name: {name}
pack: {pack}

# Current version. Used by publish if --version is not passed on the CLI.
version: "1.0.0"

# Platform IDs and slugs. Required for import, create, and publish.
# Set id to null if the project does not yet exist on that platform.
curseforge:
  id: null
  slug: {pack}

modrinth:
  id: null
  slug: {pack}

planetminecraft:
  id: null
  slug: {pack}

"""


def run_init(directory: Path) -> None:
    name, pack = _derive_identity(directory)

    # Puppy home: {directory}/puppy/
    puppy_home = directory / "puppy"
    puppy_home.mkdir(parents=True, exist_ok=True)

    _write_if_missing(puppy_home / "auth.yaml", _AUTH_YAML)
    _write_if_missing(puppy_home / ".gitignore", _GITIGNORE)
    _write_if_missing(puppy_home / "puppy.yaml", _global_puppy_yaml(name))

    # Project source: {directory}/puppy/{name}/puppy/
    project_source = puppy_home / name / "puppy"
    project_source.mkdir(parents=True, exist_ok=True)

    _write_if_missing(project_source / "puppy.yaml", _project_puppy_yaml(name, pack))
    _write_if_missing(project_source / "description.md", _DESCRIPTION_MD)

    for site, (fname, content) in _SITE_TEMPLATES.items():
        site_dir = project_source / site
        site_dir.mkdir(exist_ok=True)
        _write_if_missing(site_dir / fname, content)


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f"WARNING: {path} already exists — left untouched")
        return
    path.write_text(content)
    print(f"Created {path}")
