# Puppy — Outstanding Work

## Cleanup

- **Remove "e.g." and "i.e." from spec and code comments**: Replace with plain English ("for example", "that is").

## Unimplemented Features

- **PMC mod support**: PMC supports mods; unclear if it's a popular destination.
  When implementing, check what URL segments and form fields PMC uses for mods vs packs.

- **Modpack support (maybe, maybe never)**: Modpacks involve distinct upload formats (`.mrpack`, CF modpack zip) that differ significantly from mods and resource packs.

- **Handle other VCS systems**: Currently assumes git for the auth.yaml gitignore check.
  Should detect Mercurial, SVN, etc., or gracefully handle non-VCS directories.
  Add `--skip-auth-check` flag to bypass for unknown or non-existent VCS.

## Testing Gaps

- **API mocks**: Add reusable fixtures that intercept `urllib.request.urlopen` calls to `api.modrinth.com`, `authors.curseforge.com`, and the CF description API.
  Would let tests cover `needs_upload`, `resolve_id`, and donation/tag expansion without hitting the network.
