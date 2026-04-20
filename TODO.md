# Puppy — Outstanding Work

## Bugs / Correctness

- ✅ **Per-site rendering in `run_push`**: Fixed. Each site now rendered separately with correct tag translation.
- ✅ **Modrinth URL type in cross-linking**: Fixed. Set `modrinth.type: resourcepack` (or `modpack` etc.) in `puppy.yaml`; defaults to `mod`.

## Unimplemented Features

- **Neutral pack metadata** (spec 6.7): ✅ `resolution:`, `progress:`, `license:` implemented. `category:` skipped — taxonomy too different between sites.

## `init` Action

- ✅ Stale `strings:` comment removed from generated `puppy.yaml`.
- ✅ Per-site template wrappers (`curseforge/description.html`, `modrinth/description.md`, `planetminecraft/description.bbcode`) now created by `init`.

## Testing Gaps

- ✅ **Batch mode**: Unit tests added for batch execution, site filtering, zip links, variable isolation.
- ✅ **`create`, `import`, publisher staging**: Unit tests added.
- **Integration tests on live sites**: End-to-end `create`, `import`, and `push --pack` against real CurseForge, Modrinth, and PMC accounts.
