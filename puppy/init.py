from pathlib import Path

from puppy.sites import SITES


def _auth_yaml() -> str:
    entries = '\n'.join(s.auth_yaml_entry() for s in SITES)
    return (
        '# auth.yaml — API credentials. NEVER commit this file.\n'
        '# Listed in .gitignore — puppy will refuse to run if it is not.\n\n'
        + entries
    )

_GITIGNORE = 'auth.yaml\n'

_DESCRIPTION_MD = """\
<!-- Add your pack description here. Jinja2 variables from puppy.yaml are available,
     Example: {{ version }}, {{ name }}. Conditionals: {% if key %}...{% endif %} -->
"""

# TODO: consider --scaffold option to also create site subdirs with starter templates


def _puppy_yaml(name: str, pack: str) -> str:
    site_entries = '\n'.join(s.puppy_yaml_entry(pack) for s in SITES)
    return (
        f'# puppy.yaml — configuration for {name}.\n\n'
        f'name: {name}\n'
        f'pack: {pack}\n\n'
        '# Current version. Used by publish if --version is not passed on the CLI.\n'
        'version: "1.0.0"\n\n'
        '# Neutral metadata — expanded to site-specific fields automatically.\n'
        'resolution:\n'
        'progress:\n'
        'license:\n'
        'donation:\n'
        '  patreon:  # URL\n'
        'links:\n'
        '  home:    # project home page URL\n'
        '  source:  # source repository URL\n'
        '  issues:  # issue tracker URL\n\n'
        '# Platform IDs and slugs. Required for import, create, and publish.\n'
        '# Set id to null if the project does not yet exist on that platform.\n'
        + site_entries
    )


def run_init(directory: Path) -> None:
    name, pack = _derive_identity(directory)

    puppy_home = directory / 'puppy'
    puppy_home.mkdir(parents=True, exist_ok=True)

    _write_if_missing(puppy_home / 'auth.yaml', _auth_yaml())
    _write_if_missing(puppy_home / '.gitignore', _GITIGNORE)
    _write_if_missing(puppy_home / 'puppy.yaml', _puppy_yaml(name, pack))
    _write_if_missing(puppy_home / 'description.md', _DESCRIPTION_MD)


def _derive_identity(directory: Path) -> tuple[str, str]:
    dir_name = directory.name
    if dir_name == dir_name.lower():
        return dir_name.title(), dir_name
    return dir_name, dir_name.lower()


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f'WARNING: {path} already exists — left untouched')
        return
    path.write_text(content)
    print(f'Created {path}')
