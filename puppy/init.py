from pathlib import Path

from puppy.sites import SITES


def _auth_yaml() -> str:
    entries = '\n'.join(s.auth_yaml_entry() for s in SITES)
    return (
        '# auth.yaml — API credentials. NEVER commit this file.\n'
        '# Listed in .gitignore — puppy will refuse to run if it is not.\n\n'
        + entries
    )


_GITIGNORE = 'auth.yaml\nhashes.yaml\n'

_DESCRIPTION_MD = """\
<!-- Add your project description here. Jinja2 variables from puppy.yaml are available,
     Example: {{ version }}, {{ name }}. Conditionals: {% if key %}...{% endif %} -->
"""


def _puppy_yaml(name: str, handle: str, project_type: str) -> str:
    from puppy.project_type import PROJECT_TYPES
    pt = PROJECT_TYPES.get(project_type)
    if pt is None:
        raise SystemExit(f'Unknown project type: {project_type!r}. Valid: pack, mod, world')

    supported_sites = [s for s in SITES if s.supports(project_type)]
    site_entries = '\n'.join(s.puppy_yaml_entry(handle) for s in supported_sites)

    type_fields = ''
    if project_type in ('pack', 'world'):
        type_fields += 'progress:\n'
    if project_type == 'pack':
        type_fields += 'resolution:\n'
    if project_type == 'mod':
        type_fields += 'loaders:\n'

    return (
        f'# puppy.yaml — configuration for {name}.\n\n'
        f'name: {name}\n'
        f'handle: {handle}\n'
        f'type: {project_type}\n\n'
        '# One-line project summary shown in site listings.\n'
        'summary:\n\n'
        '# Current version. Used by publish if --version is not passed on the CLI.\n'
        'version: "1.0.0"\n\n'
        '# Neutral metadata — expanded to site-specific fields automatically.\n'
        + type_fields +
        'license:\n'
        'links:\n'
        '  home:             # project home page URL\n'
        '  source:           # source repository URL\n'
        '  issues:           # issue tracker URL\n'
        '  wiki:             # wiki/docs URL\n'
        '  patreon:          # donation URL\n'
        '  kofi:             # donation URL\n'
        '  github_sponsors:  # GitHub Sponsors URL\n'
        'socials:\n'
        '  discord:          # Discord server URL\n\n'
        '# Platform IDs and slugs. Required for pull, create, and push.\n'
        '# Set id to null if the project does not yet exist on that platform.\n'
        + site_entries
    )


def run_init(directory: Path, project_type: str) -> None:
    name, handle = _derive_identity(directory)

    puppy_home = directory / 'puppy'
    puppy_home.mkdir(parents=True, exist_ok=True)

    _write_if_missing(puppy_home / 'auth.yaml', _auth_yaml())
    _write_if_missing(puppy_home / '.gitignore', _GITIGNORE)
    _write_if_missing(puppy_home / 'puppy.yaml', _puppy_yaml(name, handle, project_type))
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
