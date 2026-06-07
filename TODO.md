# Puppy — Outstanding Work

## Cleanup

- **Remove "e.g." and "i.e." from spec and code comments**: Replace with plain English ("for example", "that is").

## Unimplemented Features

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

- **World/save specialized metadata per site**: Current world support covers only the fields shared with packs.
  Each site has world-specific metadata not yet implemented:
  - PMC: world genre categories (Adventure, Survival, Creation, Puzzle, etc. — need numeric IDs), Bedrock edition boolean, any other world-form-only fields
  - CF: verify correct world subcategory IDs and any world-specific API fields
  - MR: verify world-specific categories and any other world-only fields
  Audit each site's world create/edit form before implementing.

- **Bedrock edition support**: PMC (and possibly other sites) have a flag for Bedrock compatibility.
  Add as `planetminecraft.bedrock: true/false` (PMC-specific for now).
  Extend to other sites if they have an equivalent.

- **PMC mod support**: PMC supports mods; unclear if it's a popular destination.
  When implementing, check what URL segments and form fields PMC uses for mods vs packs.

- **Modpack support (maybe, maybe never)**: Modpacks involve distinct upload formats (`.mrpack`, CF modpack zip) that differ significantly from mods and resource packs.

- **Handle other VCS systems**: Currently assumes git for the auth.yaml gitignore check.
  Should detect Mercurial, SVN, etc., or gracefully handle non-VCS directories.
  Add `--skip-auth-check` flag to bypass for unknown or non-existent VCS.

## UX

- **Manual cookie fallback**: Add instructions for users who can't use Firefox (DevTools steps for Chrome/Safari).

## Known Limitations

- **PMC description pull**: PMC blocks non-browser HTTP, so the description can't be fetched.
  No workaround currently — users must paste content manually into `puppy/planetminecraft/description.bbcode`.

## Testing Gaps

- **API mocks**: Add reusable fixtures that intercept `urllib.request.urlopen` calls to `api.modrinth.com`, `authors.curseforge.com`, and the CF description API.
  Would let tests cover `needs_upload`, `resolve_id`, and donation/tag expansion without hitting the network.

- **Integration tests on live sites**: End-to-end `create`, `pull`, and `push --pack` against real CurseForge, Modrinth, and PMC accounts.
