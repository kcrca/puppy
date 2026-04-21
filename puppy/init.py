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
    site_entries = '\n'.join(s.puppy_yaml_entry(pack) for s in SITES)
    return (
        f'# puppy.yaml — project configuration for {name}.\n\n'
        f'name: {name}\n'
        f'pack: {pack}\n\n'
        '# Current version. Used by publish if --version is not passed on the CLI.\n'
        'version: "1.0.0"\n\n'
        '# Platform IDs and slugs. Required for import, create, and publish.\n'
        '# Set id to null if the project does not yet exist on that platform.\n'
        + site_entries
        + '\n'
    )


def run_init(directory: Path) -> None:
    name, pack = _derive_identity(directory)

    # Puppy home: {directory}/puppy/
    puppy_home = directory / 'puppy'
    puppy_home.mkdir(parents=True, exist_ok=True)

    _write_if_missing(puppy_home / 'auth.yaml', _auth_yaml())
    _write_if_missing(puppy_home / '.gitignore', _GITIGNORE)
    _write_if_missing(puppy_home / 'puppy.yaml', _global_puppy_yaml(name))

    # Project source: {directory}/puppy/{name}/puppy/
    project_source = puppy_home / name / 'puppy'
    project_source.mkdir(parents=True, exist_ok=True)

    _write_if_missing(project_source / 'puppy.yaml', _project_puppy_yaml(name, pack))
    _write_if_missing(project_source / 'description.md', _DESCRIPTION_MD)

    for site in SITES:
        fname, content = site.init_template()
        site_dir = project_source / site.name
        site_dir.mkdir(exist_ok=True)
        _write_if_missing(site_dir / fname, content)


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        print(f'WARNING: {path} already exists — left untouched')
        return
    path.write_text(content)
    print(f'Created {path}')
