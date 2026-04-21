# Puppy — Outstanding Work

## Bugs / Correctness

- ✅ **Per-site rendering in `run_push`**: Fixed. Each site now rendered separately with correct tag translation.
- ✅ **Modrinth URL type in cross-linking**: Fixed. Set `modrinth.type: resourcepack` (or `modpack` etc.) in `puppy.yaml`; defaults to `mod`.

## Unimplemented Features

- **Neutral pack metadata** (spec 6.7): ✅ `resolution:`, `progress:`, `license:` implemented. `category:` skipped — taxonomy too different between sites.

## `init` Action

- ✅ Stale `strings:` comment removed from generated `puppy.yaml`.
- ✅ Per-site template wrappers (`curseforge/description.html`, `modrinth/description.md`, `planetminecraft/description.bbcode`) now created by `init`.

## Unimplemented Actions

- **`clean` action**: Reset the PackUploader worker (`git reset --hard HEAD && git clean -fd`) without pushing.

## Planned Refactors

- **`Site` class**: Centralize all per-site data and behavior into a `Site` base class + three subclasses in `sites.py`. Eliminates `if s == 'curseforge':` branches scattered across 8 files; adding site #4 becomes a single class definition. Plan: `~/.claude/plans/elegant-munching-curry.md`.

## Design Questions

- **Jinja conditional wrapping**: No clean syntax for wrapping text in tags conditionally. Options: macro+call block, repeated `{% if %}` tags, or a custom Jinja extension. Verbose in current form.


- **Site abbreviations**: `cf`, `mr`, `pmc` added as aliases — reconsider whether this is a good idea.

## UX

- ✅ **Worker output buffering**: Fixed. Now uses `Popen` with line-by-line reading.

- **Default verbosity**: Consider making `-v` the default since uploads take a while and silence is confusing. Currently requires explicit `-v` flag.

## Testing Gaps

- Have tests use yaml package instead of writing out yaml in text
- ✅ **Batch mode**: Unit tests added for batch execution, site filtering, zip links, variable isolation.
- ✅ **`create`, `import`, publisher staging**: Unit tests added.
- **Integration tests on live sites**: End-to-end `create`, `import`, and `push --pack` against real CurseForge, Modrinth, and PMC accounts.
- **CLI-based staging tests**: `test_import_staging.py`, `test_create_staging.py`, `test_publisher_staging.py`, and `test_hygiene.py` call internal functions directly instead of going through `run_puppy`. Rewrite to use the CLI.
