# Puppy — Outstanding Work

## Cleanup

- **Remove "e.g." and "i.e." from spec and code comments**: Replace with plain English ("for example", "that is").

## Unimplemented Features

- **Modpack support (maybe, maybe never)**: Modpacks involve distinct upload formats (`.mrpack`, CF modpack zip) that differ significantly from mods and resource packs.

- **Handle other VCS systems**: Currently assumes git for the auth.yaml gitignore check.
  Should detect Mercurial, SVN, etc., or gracefully handle non-VCS directories.
  Add `--skip-auth-check` flag to bypass for unknown or non-existent VCS.

- **Per-site image galleries (low priority)**: `images.yaml` is project-or-global only
  (lookup: `<project>/puppy/images.yaml`, `<project>/puppy/images/images.yaml`, then
  `<puppy_home>/images.yaml`); there is no `<site>/images.yaml`, so a gallery can't differ
  per site. Add a site-level `images.yaml` layered over the project one — galleries are
  cohesive ordered lists, so "layering" means the more-specific file replaces the whole
  list, not a per-image merge.
  Fix the related precedence wart at the same time: today a project `images.yaml` *file*
  overwrites an inline `images:` from a more-specific `puppy.yaml` layer
  (`config.py` runs `config['images'] = images` after the layer merge), which is backwards —
  more-specific should win, consistent with the rest of the config model.

## Testing Gaps

- **API mocks**: Add reusable fixtures that intercept `urllib.request.urlopen` calls to `api.modrinth.com`, `authors.curseforge.com`, and the CF description API.
  Would let tests cover `needs_upload`, `resolve_id`, and donation/tag expansion without hitting the network.
