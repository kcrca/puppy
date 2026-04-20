# Puppy — Outstanding Work

## Bugs / Correctness

- **Per-site rendering in `run_push`**: `render()` is called once with `site=` set to the `-s` filter (or `None`). Tag translation therefore only works when `-s` is specified. Real pushes need per-site rendering so each site gets correct tag conversion.
- **Modrinth URL type in cross-linking**: ✅ Fixed. Set `modrinth.type: resourcepack` (or `modpack` etc.) in `puppy.yaml`; defaults to `mod`.

## Unimplemented Features

- **`.puppyignore`**: Spec section 6.6 — prevent large/irrelevant files from being staged into the worker directory.
- **Neutral pack metadata** (spec 6.7): Top-level `license:`, `resolution:`, `category:` keys translated to per-site fields. Clean mappings exist for `license` (needs cross-reference table) and `resolution`. Category taxonomy differs too much between sites for a full mapping.

## `init` Action

- ✅ Stale `strings:` comment removed from generated `puppy.yaml`.
- ✅ Per-site template wrappers (`curseforge/description.html`, `modrinth/description.md`, `planetminecraft/description.bbcode`) now created by `init`.

## Testing Gaps

- **Publisher (`push --pack`)**: CF and PMC upload paths implemented but untested end-to-end.
- **Batch mode**: Multiple projects under `projects:` untested.
- **`create` and `import`**: Implemented but not recently exercised against live sites.
