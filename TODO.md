# Puppy — Outstanding Work

## Unimplemented Features

- **Handle other VCS systems**: Currently assumes git for the auth.yaml gitignore check. Should detect Mercurial, SVN, etc., or gracefully handle non-VCS directories.
- **`--skip-auth-check` flag**: Bypass the auth.yaml gitignore check for unknown or non-existent VCS systems.

## Design Questions

- **Jinja conditional wrapping**: No clean syntax for wrapping text in tags conditionally. Options: macro+call block, repeated `{% if %}` tags, or a custom Jinja extension. Verbose in current form.
- **Site abbreviations**: `cf`, `mr`, `pmc` added as aliases — reconsider whether this is a good idea.

## UX

- **Default verbosity**: Consider making `-v` the default since uploads take a while and silence is confusing. Currently requires explicit `-v` flag.

## Testing Gaps

- Have tests use yaml package instead of writing out yaml in text
- **Integration tests on live sites**: End-to-end `create`, `import`, and `push --pack` against real CurseForge, Modrinth, and PMC accounts.
- **CLI-based staging tests**: `test_import_staging.py`, `test_create_staging.py`, `test_publisher_staging.py`, and `test_hygiene.py` call internal functions directly instead of going through `run_puppy`. Rewrite to use the CLI.
