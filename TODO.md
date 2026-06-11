# Puppy — Outstanding Work

## Cleanup

- **Remove "e.g." and "i.e." from spec and code comments**: Replace with plain English ("for example", "that is").

## Unimplemented Features

- **Rename `--pack` option**: `push --pack` is confusing since "pack" means resource pack elsewhere. Find a clearer name (e.g. `--file`, `--upload`, `--release`).

- **Paralell work**: Do work in parallel.
  At least across the sites, we may need to linearize accss to each site.
  Start with this, then later see if we can do per-site requests in parellel.

- **`convert` command**: Convert between description formats — `.bbcode` → `.md`, `.html` → `.md` — using existing transformers plus a well-respected HTML-to-Markdown library for the HTML case.
  Useful after importing a description manually from PMC or CurseForge.

- **Duplicate check on `create` (CF and PMC)**: Before creating, warn the user that duplicates are possible on sites without unique name enforcement.
  For CF, search by name (filtered to texture packs) and show matches, asking if theirs is one of them or a new project — if an existing ID is chosen, run pull instead.
  For PMC there is no API, so only a manual reminder is possible.
  `--force` should skip any interactive check.
  Modrinth is not a concern — its API rejects duplicate slugs cleanly.

- **CurseForge Bedrock support**: Investigate whether the `minecraft/texture-packs` and `minecraft/worlds` sections on CF allow Bedrock version IDs in the `gameVersions` list on file uploads.
  Check the game versions API response (with a real token) for Bedrock version entries alongside Java versions.
  If supported, wire `bedrock: true` neutral field to CF file upload.

- **World/save specialized metadata per site**: Current world support covers only the fields shared with packs.
  MR does not support world projects.
  Each site has world-specific metadata not yet implemented:
  - PMC: world genre categories (Adventure, Survival, Creation, Puzzle, etc. — need numeric IDs), any other world-form-only fields
  - CF: subcategory IDs verified correct; audit world create/edit API for any world-specific fields beyond shared pack fields
  Audit each site's world create/edit form before implementing.

- **PMC mod support**: PMC supports mods; unclear if it's a popular destination.
  When implementing, check what URL segments and form fields PMC uses for mods vs packs.

- **Modpack support (maybe, maybe never)**: Modpacks involve distinct upload formats (`.mrpack`, CF modpack zip) that differ significantly from mods and resource packs.

- **Handle other VCS systems**: Currently assumes git for the auth.yaml gitignore check.
  Should detect Mercurial, SVN, etc., or gracefully handle non-VCS directories.
  Add `--skip-auth-check` flag to bypass for unknown or non-existent VCS.

## UX

## Known Limitations

## Testing Gaps

- **API mocks**: Add reusable fixtures that intercept `urllib.request.urlopen` calls to `api.modrinth.com`, `authors.curseforge.com`, and the CF description API.
  Would let tests cover `needs_upload`, `resolve_id`, and donation/tag expansion without hitting the network.

- **Integration tests on live sites**: Framework in place (`tests/integration/`).
  Add `tests/integration/auth.yaml` with test account credentials and run `pytest tests/integration/`.
  CF and PMC tests need manual project cleanup after each run (no delete API).
  Investigate CF and PMC delete endpoints to automate cleanup.
