# Integration Tests

## File structure

Checked in to `tests/integration/`:

```
puppy/
├── puppy.yaml          # home config: projects list + all universal neutral fields
├── .gitignore          # ignores auth.yaml
├── auth.yaml           # gitignored; populated via `puppy auth`
├── puppypack/
│   ├── puppy.yaml      # all neutral fields applicable to packs
│   ├── description.md  # markdown with bold, italic, header, subsection
│   ├── images.yaml
│   └── images/
│       ├── img1.png    # small images (speed)
│       ├── img2.jpg
│       └── img3.png
├── puppymod/
│   ├── puppy.yaml      # all neutral fields applicable to mods
│   ├── description.md
│   ├── images.yaml
│   └── images/
│       ├── img1.png
│       ├── img2.jpg
│       └── img3.png
└── puppyworld/
    ├── puppy.yaml      # all neutral fields applicable to worlds
    ├── description.md
    ├── images.yaml
    └── images/
        ├── img1.png
        ├── img2.jpg
        └── img3.png
puppypack/
├── icon.png            # square, ≥128×128
└── puppypack.zip       # minimal valid pack
puppymod/
├── icon.png
└── puppymod.jar        # minimal valid mod (blank or stub)
puppyworld/
├── icon.png
└── puppyworld.zip      # minimal valid world save
```

The three descriptions must differ from each other.
Each `puppy/*/description.md` should exercise: bold, italic, a header, a subsection.
The `{{ img('img1') }}` reference is added to the description in the push step (step 6) — not checked in initially.

Create test accounts on each site for integration testing.
Populate `puppy/auth.yaml` by running `puppy auth` from `tests/integration/`.

---

## Test sequence

### Step 1 — Clean up prior runs

Remove all `puppy-test-*` projects from all site accounts:

- **Modrinth**: `GET /v2/user` (authed) → username → `GET /v2/user/{username}/projects` →
  filter slugs starting `puppy-test-` → `DELETE /v2/project/{id}` for each.
- **CurseForge**: no delete API — print slugs found for manual removal at curseforge.com/my-projects.
- **PMC**: no delete API — print project IDs found for manual removal at planetminecraft.com.

### Step 2 — Prepare tmp tree

Copy the entire `tests/integration/` tree into a `tmp/` directory.
Run all subsequent steps from within `tmp/`.

### Step 3 — Inject slugs

Generate a timestamp: `YY-MM-DD-HH-mm` (e.g. `26-06-07-14-30`).

Write `pack:` into each project's `puppy.yaml`:
- `puppypack-26-06-07-14-30`
- `puppymod-26-06-07-14-30`
- `puppyworld-26-06-07-14-30`

Record the slugs — used later to verify round-trips.

### Step 4 — Create projects

For each project, run:

```
puppy create --site <sites>
```

This registers the project on each site and immediately pushes description, icon, and metadata (but not gallery images, and not the pack file).

Sites per project type:
- pack: Modrinth, CurseForge, PMC
- mod: Modrinth, CurseForge (PMC mod support TBD)
- world: Modrinth, CurseForge, PMC

### Step 5 — Validate public pages (Playwright + BeautifulSoup)

For each project × each applicable site, load the public project page and assert:

- Project name matches
- Summary/tagline matches
- License displayed correctly
- Categories/tags match
- Resolution tag (pack/world)
- All links present (home, source, etc.)
- All socials present (ko-fi, discord, etc.)
- Icon: present and not broken
- Gallery: no images yet (none uploaded)
- Description: bold, italic, header, subsection all rendered

### Step 6 — Pull

For each project, run:

```
puppy pull --site <sites>
```

Assert `puppy.yaml` contains expected harvested values:
name, summary, license, site-assigned ID/slug, site-specific fields (resolution, categories, etc.).

### Step 7 — Modify and push with images

For each project:

1. Append a new sentence to `description.md`.
2. Also append `{{ img('img1') }}` to `description.md` (will resolve to CDN URL after upload).
3. Change `summary` in `puppy.yaml` to a new value.
4. Run:

   ```
   puppy push --site <sites> --images
   ```

   Gallery images are uploaded first; CDN URLs become available to the renderer for `{{ img('img1') }}`.

### Step 8 — Validate updated pages (Playwright + BeautifulSoup)

Repeat page validation (step 5) for each project × each site.
Additionally assert:

- Description contains the new sentence.
- Description contains a rendered image (not empty).
- Summary reflects the new value.
- Gallery: one or more images visible and not broken.

### Step 9 — Pull with images

For each project, run:

```
puppy pull --site <sites> --images
```

Assert:
- Updated summary in `puppy.yaml`.
- `images/images.yaml` written with at least one entry.

### Step 10 — Push pack file

For each project, run:

```
puppy push --site <sites> --pack --version 1.0.0
```

(Uses `.zip` / `.jar` from the project root sibling directory.)

Validate on public pages (Playwright) that the file download is available and shows version `1.0.0`.

---

## Notes

- Projects are left alive at the end of each run for inspection.
  The next run's step 1 cleans them up.
- CF and PMC projects accumulate until manually deleted (no delete API).
- Re-using slugs after deletion may be restricted on some sites; the timestamp format ensures unique slugs per run.
