# Integration Test Specification

## Test structure

Tests use a class-per-site-type layout.
Each class inherits from `LifecycleBase` (defined in `conftest.py`), which provides five ordered test methods.
Site-specific assertions are overridden in each class.
Different classes are independent and can run in parallel (e.g. `pytest-xdist --dist=class`).

| File | Classes |
|---|---|
| `test_mr.py` | `TestMRPackLifecycle`, `TestMRModLifecycle` |
| `test_cf.py` | `TestCFPackLifecycle`, `TestCFWorldLifecycle` |
| `test_pmc.py` | `test_pmc_account_empty` (standalone), `TestPMCPackLifecycle`, `TestPMCWorldLifecycle` |

All are marked `pytest.mark.integration` and require credentials in `tests/integration/puppy/auth.yaml`.

Each lifecycle class runs five tests in order:

| Method | What it exercises |
|---|---|
| `test_01_create` | `puppy create` — id/slug written to config; site metadata verified |
| `test_02_pull` | `puppy pull` — id/slug round-trip |
| `test_03_push_images` | `puppy push --images` — description body, icon, gallery, donation, discord |
| `test_04_pull_images` | `puppy pull --images` — summary and images.yaml updated |
| `test_05_push_pack` | `puppy push --pack` — version file appears on site |

State (project dir, project id) is shared between test methods within a class via a class-scoped `ctx` fixture.
If an earlier test fails, later tests in the same class will also fail (no explicit skip-on-failure guards).

---

## What each lifecycle test covers

Each lifecycle test exercises the full create → pull → push → pull → push-pack sequence for one project type on one site.
A timestamp-based slug is injected per run to keep projects unique and cleanable.

### create
- `id` (and `slug` where the site returns one) written back to `puppy.yaml`
- Metadata sent during create verifiable via API: title, summary, categories
- Modrinth also: `license.id`, `source_url`, `discord_url`
- CurseForge also: `primaryCategoryId`
- PMC: project name present on authenticated management page

### pull (first)
- `id` and `slug` round-trip correctly (still present in `puppy.yaml` after pull)

### push --images
- Description body updated (new sentence appended to `description.md`)
- Modrinth: `body` contains new sentence, `icon_url` set, gallery non-empty, `donation_urls` contains ko-fi
- Modrinth mod: `discord_url` reflects `modrinth.discord` per-site override (not neutral `socials.discord`)
- Modrinth pack: `discord_url` reflects neutral `socials.discord`
- CurseForge: `summary` updated (body conditional — see CF notes below)
- PMC: project name still present on management page

### pull --images
- `summary` in `puppy.yaml` updated (MR, CF)
- `images/images.yaml` written with at least one entry (MR, PMC always; CF conditional)

### push --pack
- Modrinth: version with `version_number: 1.0.0` present; `changelog` matches `puppy.yaml`; mod: `loaders` contains `fabric`
- CurseForge: file with `displayName` containing `v1.0.0` in project files list
- PMC: `.publish_state.yaml` records `planetminecraft.version == 1.0.0`

---

## test_pmc_account_empty

Runs before PMC lifecycle tests.
Loads both PMC management listing pages via Playwright and asserts zero project links.
Fails as a test (not a fixture error) if cleanup left projects — other tests still run.

---

## Fixture data

```
tests/integration/puppy/
├── puppy.yaml          # home config: shared neutral fields (license, links, socials, changelog)
├── puppypack/
│   ├── puppy.yaml      # pack-specific neutral fields; no modrinth.discord (uses neutral)
│   ├── description.md
│   ├── icon.png
│   ├── images.yaml + images/
├── puppymod/
│   ├── puppy.yaml      # mod-specific fields; modrinth.discord set (tests per-site override)
│   ├── description.md
│   ├── icon.png
│   ├── images.yaml + images/
└── puppyworld/
    ├── puppy.yaml
    ├── description.md
    ├── icon.png
    ├── images.yaml + images/
tests/integration/puppypack/puppypack-1.0.0.zip   # artifact for pack push --pack
tests/integration/puppymod/puppymod-1.0.0.jar     # artifact for mod push --pack
tests/integration/puppyworld/puppyworld-1.0.0.zip # artifact for world push --pack
```

Artifacts are made unique per test session by appending `puppy-run-id.txt` to each zip/jar.
This avoids Modrinth's global file-hash deduplication rejecting re-uploads across runs.

---

## Cleanup (session start)

Runs once per session before any tests, deleting all stale test projects.

- **Modrinth**: API `DELETE /v2/project/{id}` for all projects matching the slug pattern.
- **CurseForge**: `DELETE _CF_DASH/projects/{id}` for all projects matching the slug pattern.
- **PMC**: Playwright — loads both management listing pages, navigates to each project's manage page,
  clicks "Delete", confirms in the modal, then waits 3 s and re-lists to check all are gone.
  Prints a warning if any remain (verified separately by `test_pmc_account_empty`).

---

## Site-specific notes

### Modrinth
- Projects created as drafts (`is_draft: true`) — not publicly visible.
  All validation uses the authenticated API.
- `client_side` / `server_side` always return `'unknown'` from the MR API regardless of what was sent — don't assert these.
- File-hash deduplication is global: the same zip/jar bytes cannot be uploaded to any MR project twice.

### CurseForge
- Authors API (`authors.curseforge.com/_api`) does not expose `licenseId`, social links, or donation URLs.
  These fields are sent during create/push but cannot be read back via this endpoint — they are not asserted.
- Description body check (`GET /v1/mods/{id}/description`) is conditional: newly created projects
  may not be approved yet; skip if the endpoint returns no data.
- `images/images.yaml` after pull is conditional: gallery may not be available until the project is approved.
- File upload may return a transient 403 (empty body) under rate limiting.
  Retried up to 3 times with a 5 s back-off.
- `category` in `puppy.yaml` may be an integer (bare category ID) or a string name.

### Planet Minecraft
- Texture packs are held in a moderation queue after creation — the public page is not immediately accessible.
  All PMC validation uses the authenticated management page via Playwright.
- PMC has a daily version-log submission limit.
  If `push --pack` (step 10) fails with "daily update limit reached", wait until the next day.
- Only packs and worlds are supported (no mod type on PMC).
