# Integration Test Specification

## How to run

Integration tests are excluded from the default `pytest` run.
Run them in parallel (recommended):

```bash
pytest tests/integration/ --dist=class -n auto
```

Or serially:

```bash
pytest tests/integration/
```

Credentials must be present in `tests/integration/puppy/auth.yaml` (same format as a real `auth.yaml`).
Tests for sites with missing credentials are automatically skipped.
To run only one site:

```bash
pytest tests/integration/ -k pmc --dist=class -n auto
pytest tests/integration/ -k cf  --dist=class -n auto
pytest tests/integration/ -k mr  --dist=class -n auto
```

Cleanup runs automatically at the start of each session (deletes all projects on the test accounts).
To clean up outside a test run:

```bash
python tests/integration/cleanup.py            # all sites
python tests/integration/cleanup.py --site mr
python tests/integration/cleanup.py --site cf
python tests/integration/cleanup.py --site pmc
```

---

## Parallel execution

`--dist=class` (pytest-xdist) assigns every test in a class to one worker.
This is required: the five lifecycle tests in each class are ordered and share state — they must run sequentially on one worker.
Different classes run on separate workers concurrently.

Session cleanup (`_cleanup_prior_runs`) runs only on the master process or `gw0`.
Without this guard, every xdist worker would run cleanup concurrently and race each other.
Serial runs (no `-n`) behave identically because `workerid` defaults to `'master'`.

---

## Error handling

When a puppy command hits an auth failure or site usage limit, the test **skips** (not fails) with a clear message.
All remaining tests in the same class also skip automatically.

**Auth failures** — triggered by:
- `AuthExpiredError` raised by any site (for example HTTP 401, 403, or CF's 400 `"Forbidden"`)
- `SystemExit` whose message contains `"auth expired"`

Skip message names the site and HTTP status and points to `tests/integration/puppy/auth.yaml`.

**Usage limit failures** — triggered by:
- `SystemExit` whose message contains `"daily update limit"` (PMC limits version submissions per day)

Both cases store the reason in `ctx['_auth_error']`.
Every subsequent `_run()` call checks that key and skips immediately without invoking puppy.
This prevents cascading failures when credentials are stale or a limit is hit mid-run.

---

## Test structure

Tests use a class-per-site-type layout.
Each class inherits from `LifecycleBase` (defined in `conftest.py`), which provides five ordered test methods.
Site-specific assertions are overridden in each class.
Different classes are independent and run in parallel under `--dist=class`.

| File | Standalone tests | Classes |
|---|---|---|
| `test_mr.py` | `test_mr_account_empty` | `TestMRPackLifecycle`, `TestMRModLifecycle` |
| `test_cf.py` | `test_cf_account_empty` | `TestCFPackLifecycle`, `TestCFWorldLifecycle`, `TestCFBedrockPackLifecycle`, `TestCFBedrockWorldLifecycle` |
| `test_pmc.py` | `test_pmc_account_empty` | `TestPMCPackLifecycle`, `TestPMCWorldLifecycle`, `TestPMCBedrockPackLifecycle`, `TestPMCBedrockWorldLifecycle` |

All are marked `pytest.mark.integration` and require credentials in `tests/integration/puppy/auth.yaml`.

Each lifecycle class runs five tests in order:

| Method | What it exercises |
|---|---|
| `test_01_create` | `puppy create` — id/slug written to config; site metadata verified |
| `test_02_pull` | `puppy pull` — id/slug round-trip |
| `test_03_push_images` | `puppy push --images` — description body, summary, links, license, icon, gallery, donation, discord |
| `test_04_pull_images` | `puppy pull --images` — summary, license, links, socials, images.yaml written back |
| `test_05_push_pack` | `puppy push --pack` — version file appears on site |

State (project dir, project id) is shared between test methods within a class via a class-scoped `ctx` fixture.
Auth and limit errors propagate as skips to all remaining tests in the class — see "Error handling" above.

---

## What each lifecycle test covers

Each lifecycle test exercises the full create → pull → push → pull → push-pack sequence for one project type on one site.
A timestamp-based slug is injected per run to keep projects unique and cleanable.

### create
- `id` (and `slug` where the site returns one) written back to `puppy.yaml`
- Metadata sent during create verifiable via API: title, summary, categories
- Modrinth also: `license.id`, `source_url`, `discord_url`
- CurseForge also: `primaryCategoryId`; bedrock classes also: `classId == 4559`, `curseforge.bedrock: true` in `puppy.yaml`
- PMC: project name present on authenticated management page; bedrock classes also: `planetminecraft.bedrock: true` in `puppy.yaml`

### pull (first)
- `id` and `slug` round-trip correctly (still present in `puppy.yaml` after pull)
- CurseForge bedrock: `curseforge.bedrock: true` still present after pull
- PMC bedrock: `planetminecraft.bedrock: true` still present after pull

### push --images
- Description body updated (new sentence appended to `description.md`)
- Modrinth: `body` contains new sentence; `description` (summary) updated; `source_url`, `issues_url`, `wiki_url` all set; `license.id` == MIT; `icon_url` set; gallery non-empty; `donation_urls` contains ko-fi
- Modrinth mod: `discord_url` reflects `modrinth.discord` per-site override (not neutral `socials.discord`)
- Modrinth pack: `discord_url` reflects neutral `socials.discord`
- CurseForge: `summary` updated
- PMC: project name still present on management page

### pull --images
- Modrinth: `summary`, `license`, `links.source`, `links.issues`, `links.wiki`, `socials.discord` all written back to `puppy.yaml`
- Modrinth mod: `socials.discord` reflects the per-site `modrinth.discord` value (what MR actually stored)
- CurseForge: `summary` updated
- `images/images.yaml` written with at least one entry (MR, PMC always; CF conditional)

### push --pack
- Modrinth: version with `version_number: 1.0.0` present; `changelog` matches `puppy.yaml`; mod: `loaders` contains `fabric`
- CurseForge: file with `displayName` containing `v1.0.0` in project files list
- PMC: `.publish_state.yaml` records `planetminecraft.version == 1.0.0`

---

## Account-empty tests

Each site has a standalone `test_<site>_account_empty` that runs after session cleanup and asserts no stale test projects remain.
Fails as a test (not a fixture error) so other tests still run on partial cleanup.

- **MR**: queries `/user/{username}/projects`, matches against the test slug pattern.
- **CF**: queries the authors dash project list, matches against both test slug patterns.
- **PMC**: loads both management listing pages via Playwright, checks for project links.

---

## Fixture data

```
tests/integration/puppy/
├── puppy.yaml          # home config: shared neutral fields (license, links, socials, changelog)
├── puppypack/
│   ├── puppy.yaml      # pack-specific neutral fields; no modrinth.discord (uses neutral)
│   ├── description.md
│   ├── icon.png
│   ├── images.yaml     # gallery manifest
│   └── images/         # img1.png, img2.jpg, img3.png
├── puppymod/
│   ├── puppy.yaml      # mod-specific fields; modrinth.discord set (tests per-site override)
│   ├── description.md
│   ├── icon.png
│   ├── images.yaml
│   └── images/
└── puppyworld/
    ├── puppy.yaml
    ├── description.md
    ├── icon.png
    ├── images.yaml
    └── images/
tests/integration/puppypack/puppypack-1.0.0.zip   # artifact for pack push --pack
tests/integration/puppymod/puppymod-1.0.0.jar     # artifact for mod push --pack
tests/integration/puppyworld/puppyworld-1.0.0.zip # artifact for world push --pack
```

Artifacts are made unique per test session by appending `puppy-run-id.txt` to each zip/jar.
This avoids Modrinth's global file-hash deduplication rejecting re-uploads across runs.

---

## Cleanup

### Session start

Runs once per session before any tests via the `_cleanup_prior_runs` fixture, deleting **all** projects on the test accounts.

- **Modrinth**: `GET /v2/user/{username}/projects` (username from `auth.yaml` `modrinth.username`), then `DELETE /v2/project/{id}` for each.
  `GET /user` is not used — the PAT scope does not include user-read; the username must be in `auth.yaml`.
- **CurseForge**: paginates `_CF_DASH/projects` in batches of 100, then `DELETE _CF_DASH/projects/{id}` for each.
- **PMC**: Playwright — loads both management listing pages, navigates to each project's manage page,
  clicks "Delete", confirms in the modal, then waits 3 s and re-lists to check all are gone.
  Prints a warning if any remain.

## Site-specific notes

### Modrinth
- Projects created as drafts (`is_draft: true`) — not publicly visible.
  All validation uses the authenticated API.
- `client_side` / `server_side` always return `'unknown'` from the MR API regardless of what was sent — don't assert these.
- File-hash deduplication is global: the same zip/jar bytes cannot be uploaded to any MR project twice.

### CurseForge
- Authors API (`authors.curseforge.com/_api`) does not expose `licenseId`, social links, or donation URLs.
  These fields are sent during create/push but cannot be read back via this endpoint — they are not asserted.
- `images/images.yaml` after pull is conditional: gallery may not be available until the project is approved.
- File upload may return a transient 403 (empty body) under rate limiting.
  Retried up to 3 times with a 5 s back-off.
- `category` in `puppy.yaml` may be an integer (bare category ID) or a string name.
- Bedrock classes (`TestCFBedrockPackLifecycle`, `TestCFBedrockWorldLifecycle`) inject `bedrock: true` into the project config via `_extra_config()`.
  These create projects under classId 4559 (Addons); `curseforge.bedrock: true` is written to `puppy.yaml` on create and preserved through pull.

### Planet Minecraft
- Texture packs are held in a moderation queue after creation — the public page is not immediately accessible.
  All PMC validation uses the authenticated management page via Playwright.
- PMC has a daily version-log submission limit.
  If any test hits this limit, that test and all subsequent tests in the class skip automatically — wait until the next day and re-run.
- Only packs and worlds are supported (no mod type on PMC).
