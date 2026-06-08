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
The `{{ img('img1') }}` reference is added to the description in the push step (step 7) — not checked in initially.

Create test accounts on each site for integration testing.
Populate `puppy/auth.yaml` by running `puppy auth` from `tests/integration/`.

---

## Test sequence

### Step 1 — Clean up prior runs

Remove all `puppy(pack|mod|world)-YY-MM-DD-HH-mm` projects from all site accounts:

- **Modrinth**: `GET /v2/user/me` (authed) → username → `GET /v2/user/{username}/projects` →
  filter slugs matching pattern → `DELETE /v2/project/{id}` for each.
- **CurseForge**: `GET _CF_DASH/projects?filter={}&range=[0,99]&sort=["id","DESC"]` →
  filter slugs matching pattern → `DELETE _CF_DASH/projects/{id}` for each.
- **PMC**: no delete API — projects accumulate; remove manually at planetminecraft.com/dashboard/.

### Step 2 — Prepare tmp tree

Copy the entire `tests/integration/` tree into a `tmp/` directory.
Run all subsequent steps from within `tmp/`.

### Step 3 — Inject slugs

Generate a timestamp: `YY-MM-DD-HH-mm` (e.g. `26-06-07-14-30`).

Write `pack:` and `name:` into each project's `puppy.yaml`:
- `puppypack-26-06-07-14-30` / `Puppy Test Pack 26-06-07-14-30`
- `puppymod-26-06-07-14-30` / `Puppy Test Mod 26-06-07-14-30`
- `puppyworld-26-06-07-14-30` / `Puppy Test World 26-06-07-14-30`

Record the slugs — used later to verify round-trips.

### Step 4 — Create projects

For each project, run:

```
puppy create --site <sites>
```

This registers the project slot on each site and writes `id` and `slug` back to `puppy.yaml`.
Create does **not** push description body, icon, or gallery — those are pushed in step 7.

Sites per project type:
- pack: Modrinth, CurseForge, PMC
- mod: Modrinth
- world: CurseForge, PMC

Assert `puppy.yaml` contains `id` (and `slug` where returned by create).

### Step 5 — Validate metadata sent during create

For each project × each applicable site, verify the fields sent in the create call:

- **Modrinth** (authenticated API, draft not publicly visible):
  `GET /v2/project/{id}` → assert title, summary (description field), categories, additional_categories (resolution for packs).
  Body is empty — description not pushed yet.

- **CurseForge** (authors API):
  `GET _CF_DASH/projects/{id}` → assert name, summary, primaryCategoryId.
  Description body is placeholder — not pushed yet.

- **PMC** (Playwright, management page — public page held for moderation on texture packs):
  Load `/account/manage/texture-packs/{id}/` or `/account/manage/projects/{id}/` → assert project name present.

Gallery images: none uploaded yet (images pushed in step 7).

### Step 6 — Pull

For each project, run:

```
puppy pull --site <sites>
```

Assert `puppy.yaml` contains the site-assigned `id` and `slug`.

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

### Step 8 — Validate updated pages

For each project × each applicable site, load the project page and assert:

- **Modrinth**: authenticated API — title, description, body contains new sentence and rendered image, categories, icon present, gallery has images.
- **CurseForge**: authors API — name, summary reflects new value, description body contains new sentence.
- **PMC**: management page — project name present.

(Full public page validation where accessible: summary, license, categories, links, socials, icon, gallery.)

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

Validate that the file download is available and shows version `1.0.0`.

---

## Notes

- Projects are left alive at the end of each run for inspection.
  The next run's step 1 cleans them up.
- PMC projects accumulate until manually deleted (no delete API).
- Re-using slugs after deletion may be restricted on some sites; the timestamp format ensures unique slugs per run.
- Modrinth projects are created as drafts (`is_draft: true`); they are not publicly visible.
  All Modrinth validation uses the authenticated API.
- PMC texture packs are held in a moderation queue after creation; the public page is not immediately accessible.
  PMC validation uses the authenticated management page via Playwright.
