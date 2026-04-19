from pathlib import Path


_AUTH_YAML = """\
# auth.yaml — API credentials. NEVER commit this file.
# See puppy/.gitignore — auth.yaml must be listed there or puppy will refuse to run.

curseforge:
  token: YOUR_CURSEFORGE_API_TOKEN
  cookie: CobaltSession=YOUR_COBALT_SESSION_COOKIE

modrinth: YOUR_MODRINTH_TOKEN

planetminecraft: pmc_autologin=YOUR_PMC_AUTOLOGIN_COOKIE
"""

_GITIGNORE = "auth.yaml\n"


def _derive_identity(directory: Path) -> tuple[str, str]:
    dir_name = directory.name
    if dir_name == dir_name.lower():
        return dir_name.title(), dir_name
    return dir_name, dir_name.lower()


def _puppy_yaml(name: str, pack: str) -> str:
    return f"""\
# puppy.yaml — project configuration.

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

# Content fragments used in description templates.
# strings:
#   header: "{name} Header"
#   footer: "{name} Footer"
"""


def run_init(directory: Path) -> None:
    name, pack = _derive_identity(directory)
    puppy_dir = directory / "puppy"
    puppy_dir.mkdir(parents=True, exist_ok=True)

    _write_if_missing(puppy_dir / "puppy.yaml", _puppy_yaml(name, pack))
    _write_if_missing(puppy_dir / "auth.yaml", _AUTH_YAML)
    _write_if_missing(puppy_dir / ".gitignore", _GITIGNORE)


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f"WARNING: {path} already exists — left untouched")
        return
    path.write_text(content)
    print(f"Created {path}")
