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

- **`file_changed` reconcile branches**: stub the per-site network seam (`latest_file_sha`, `gallery_urls`) — not `urlopen` — and cover the out-of-band-edit reconcile path and return value for both CF and Modrinth.
  Already covered, do not re-add: `resolve_id` (`test_cf_resolve_id.py`, `test_modrinth_resolve_id.py`), retry/backoff (`test_http.py`), donation/tag expansion (pure `apply_neutral`, in `test_cf.py` / `test_neutral_metadata.py` / `test_mr.py`).
  Avoid `urlopen`-level mocks: they only prove we build/parse a canned blob, not that it matches the live API (the real drift risk) — that's the integration suite's job, so green `urlopen` mocks give false confidence.
