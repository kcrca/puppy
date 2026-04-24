# **Puppy Design Specification**

## **1. Design Principles**
* **User-Centric Simplicity:** Defaults favor the user. Puppy acts on all projects and sites unless filtered.
* **Worker-First Execution:** Puppy acts as a thin management layer for `PackUploader` (`pu`). It handles staging, factory-resetting the worker, and dependency checks automatically.
* **Implicit Discovery:** Asset discovery (icons, zips) is preferred over manual path mapping.
* **Integrated Versioning:** All data and harvested IDs reside in the project source directory.
* **Markdown-First:** Content is written in Markdown. Site-specific native files (`.html`, `.bbcode`) act as overrides.
* **Non-Interactive (Fail-Fast):** No prompts. Errors (missing IDs, mismatched versions, security flaws) result in an immediate exit.
* **Cross-Platform:** All paths and subprocesses must work on macOS, Linux, and Windows.

## **2. Core Identity & Naming**
* **`pack` (Internal Slug):** Lowercase alphanumeric only — spaces and special characters stripped. Derived from the directory name unless overridden. Example: `'Neon Glow!'` → `neonglow`.
* **`name` (Display Name):** Preserves casing and special characters exactly (`'Neon Glow!'` stays `'Neon Glow!'`). If the source string is strictly lowercase ASCII, converts to Title Case (`neon` → `Neon`).
* **Single override:** If only `name:` is provided, `pack` is derived by slugifying `name` (lowercase, strip non-alphanumerics). If only `pack:` is provided, `name` is derived by the same casing rules. Both can be set explicitly.
* **Auto-update:** Whenever a project is loaded for any action, if either `name` or `pack` was absent from `puppy.yaml`, the derived value is written back automatically.

## **3. Directory Architecture**

For a pack named "neon" the structure is:

* **Global Root:** `~/neon/`
* **Puppy Home:** `~/neon/puppy/`
* **Auth & Gitignore:** `~/neon/puppy/auth.yaml`, `~/neon/puppy/.gitignore`
* **Global Config:** `~/neon/puppy/puppy.yaml`
* **Project Root:** `~/neon/puppy/[ProjectName]/`
* **Project Source:** `~/neon/puppy/[ProjectName]/puppy/`
* **Worker Directory:** `~/PackUploader/` (the PackUploader repo — reset before each run)
* **Debug Output:** `{tempdir}/puppy/{pack}/` (used for `--dry-run`, wiped fresh each run)
* **Images:** `~/neon/puppy/images/`

### **3.1 Flat Single-Project Mode**
For a pack with only one project, `puppy.yaml` may live directly in the Puppy Home (i.e. `~/neon/puppy/puppy.yaml`) with `pack:` or `name:` set. Puppy infers the single project automatically — no `projects:` list required.

### **3.2 Running Location**
Puppy can be invoked from:
* **Global Root** (e.g. `~/neon/`) — detected by presence of `puppy/auth.yaml`
* **Puppy Home** (e.g. `~/neon/puppy/`) — detected by presence of `auth.yaml`
* **Project Root** (e.g. `~/neon/puppy/NeonGlow/`) — detected by presence of `puppy/` subdir

## **4. CLI & Actions**
`puppy [options] [action]`

### **4.1 Actions**
* **`push` (Default):** Updates metadata, summaries, descriptions, and icons. With `-p/--pack`, also uploads the zip artifact. Requires `version:` in `puppy.yaml` or `-V/--version` when using `-p`.
* **`create`:** Registers projects on sites with missing IDs. **Requires `--create` flag.**
* **`import`:** Pulls live site data and reverse-migrates to local files. Writes to `puppy.yaml` and `puppy/images/images.yaml`. Does **not** create description templates (those are created by `init`). **Description body text import varies by platform:**
  * **Modrinth:** Full description body imported via API.
  * **CurseForge:** Only the summary is imported — full HTML description not available via API.
  * **Planet Minecraft:** No description imported. Manually paste content into `puppy/planetminecraft/description.bbcode`.
* **`init`:** Creates the `puppy/` directory structure in the target directory: `puppy.yaml`, `auth.yaml`, `.gitignore`, and a starter `description.md`. Derives `name` and `pack` from the directory name. Any file that already exists is left untouched with a warning.
* **`clean`:** Resets the PackUploader worker without pushing.

### **4.2 Options & Flags**
* **`-n/--dry-run`:** Executes the full pipeline without hitting APIs or running the worker. Writes a per-site preview to `{tempdir}/puppy/{pack}/index.html` — a tabbed HTML page showing rendered descriptions, project metadata, icon, and images for each site. Also prints the `file://` URL to open it directly.
* **`-v` / `-vv`:** High-level progress (`-v`) or raw worker stdout/stderr (`-vv`).
* **`-d/--dir [path]`:** Sets working directory. Defaults to CWD.
* **`-s/--site [sitename]`:** Limits action to a specific site (e.g. `modrinth`, `curseforge`, `planetminecraft`).
* **`-V/--version [string]`:** Version string override. Falls back to `version:` in `puppy.yaml`. Artifact matched via any `.zip` in `puppy/` whose filename ends with `[-_.]version.zip`.
* **`-p/--pack`:** Include zip artifact upload in `push`. Requires `minecraft:` or `versions:` in `puppy.yaml`. Upload is skipped per-site if the artifact is already current:
  * **Modrinth:** Compares SHA-512 hash of local zip against the hash stored in the latest version's file listing.
  * **CurseForge:** Compares both version string and file size (bytes) against the most recent uploaded file; uploads if either differs.
  * **Planet Minecraft:** Compares version string against last version recorded in `puppy/.publish_state.yaml`.
* **`-f/--force`:** With `-p`, bypasses skip logic and uploads unconditionally on all sites.
* **`-y/--yes`:** Skip confirmation prompts. The `create` action prompts for confirmation unless this flag is set.
* **`--worker [path]`:** PackUploader worker directory. Defaults to `~/PackUploader`.

## **5. Cascading Configuration & Discovery**

### **5.0 auth.yaml**
`auth.yaml` stores API credentials and must never be committed. Puppy exits with a fatal error if `auth.yaml` does not exist or is not listed in `puppy/.gitignore`.

Structure mirrors PackUploader's `auth.json`:
```yaml
curseforge:
  token: ...
  cookie: CobaltSession=...
modrinth: <token>
planetminecraft: pmc_autologin=<cookie>
```

### **5.0.1 minecraft: shorthand**
`minecraft:` sets the Minecraft game version for artifact uploads across all sites. A string value is treated as an exact version (`minecraft: '26.1'` → `type: exact, version: '26.1'`). A dict value is used as-is (`minecraft: {type: latest}`). Per-site overrides via `versions:` take precedence. Required when using `push --pack` unless `versions:` is fully specified.

### **5.1 Config Merge (Additive Synthesis)**
Layers applied in order (later layers win for scalars; dicts merge additively):
1. Global Defaults (`{puppy_home}/puppy.yaml`)
2. Global Site Overrides (`{puppy_home}/[sitename]/puppy.yaml`)
3. Project Source (`{project_root}/puppy/puppy.yaml`)
4. Project Site Overrides (`{project_root}/puppy/[sitename]/puppy.yaml`)

**Batch mode:** Projects listed explicitly under `projects:` in the global `puppy.yaml`. Subdirectories are not auto-scanned.

### **5.2 Content Discovery (The Cascade)**
The description body is discovered by searching in order:
1. Project Site File (`{project_root}/puppy/[sitename]/body.{ext}`)
2. Project General File (`{project_root}/puppy/description.{ext}`)
3. Global General File (`{puppy_home}/description.{ext}`)

**Extension Priority (native format wins):** CurseForge (`.html` → `.md`); Modrinth (`.md` → `.html`); PMC (`.bbcode` → `.md`).

**PMC description format:** When the source is Markdown, Puppy converts it to PMC's BBCode dialect before staging. When the source is already `.bbcode`, it is used as-is. See Appendix B for the full PMC BBCode dialect reference.

### **5.3 Description Body vs. Template Wrapper**
Each site has two distinct files:
* **Wrapper Template** (`{project_root}/puppy/[sitename]/description.{ext}`): Scaffolding with `{{ description }}`, `{{ images }}` etc. Staged for the worker as `templates/{site}.{ext}`. Created by `init`.
* **Description Body** (`{project_root}/puppy/description.md` or `{puppy_home}/description.md`): The actual content substituted for `{{ description }}` in the wrapper. Site-specific body overrides can live at `{project_root}/puppy/[sitename]/body.{ext}`.

### **5.4 Template Variable Substitution**
Description body files are rendered as Jinja2 templates. All config keys from `puppy.yaml` are available as variables: `{{ version }}`, `{{ name }}`, `{{ modrinth.slug }}` etc. Full Jinja2 syntax is supported (`{% if %}`, `{% for %}`, filters, etc.). Unrecognised variables produce a warning and are left as-is.

**Standard config fields passed to the worker:**
* `summary:` — one-line project description shown in search results
* `optifine: true/false` — whether the pack requires OptiFine (default false)
* `video: true/false` — whether a video is associated (default false)
* `github: true/false` — whether a GitHub repo is associated (default false)

**Special image files** (placed in `{project_root}/puppy/`):
* `thumbnail.png` — hero/banner image; staged and uploaded separately from gallery images
* `logo.png` — project logo; displayed at fixed aspect ratio (1280×256)

**Image entry flags** (in `images.yaml`):
* `embed: true` — image is embedded in the description body
* `featured: true` — image is promoted as a featured/highlighted gallery image on supporting sites

### **5.5 Path Resolution Rules**
* **Internal Files:** Follow the Cascading Discovery logic above.
* **External Files:** Paths outside `puppy/` are treated as literal — no extension guessing or hierarchy search.
* **Relative Paths:** All relative paths in any YAML file are resolved relative to the project's `puppy/` directory, regardless of which subdirectory the YAML file lives in. So `../site` in `puppy/images/images.yaml` and `../site` in `puppy/puppy.yaml` both resolve to the same directory.

### **5.6 Asset Discovery**
For `create` and `push`, the icon and zip artifact are resolved as follows:
* **Explicit paths** (`icon:` and `zip:` in `puppy.yaml`): resolved relative to the project's `puppy/` directory.
* **Implicit discovery** (fallback): a single `.png` in `puppy/` (excluding `thumbnail.png` and `logo.png`) is the icon; a single `.zip` in `puppy/` is the artifact. Multiple files of either type is a fatal error.
* **Icon validation:** The icon must be a square PNG.

### **5.7 Image Metadata**
Image metadata (the list of images with names, descriptions, and file references) lives in one of two locations — both are valid, but not both simultaneously:
* **`puppy/images.yaml`** — used when images live outside the puppy directory (referenced via `source:`).
* **`puppy/images/images.yaml`** — used when image files are stored inside `puppy/images/`.

Both formats support an optional top-level `source:` key pointing to a directory (resolved relative to `puppy/`) where image files are found. If `source:` is absent, images are loaded from `puppy/images/`.

**Image format handling:** The `file` field may include or omit a file extension. If omitted, Puppy searches for any file with a recognised image extension (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, etc.). Any non-PNG source is converted to PNG using Pillow before staging, since the worker always reads `{file}.png`. If the file cannot be found or converted, Puppy exits with an error.

## **6. Operational Logic**

### **6.1 Security & Auth Protocol**
* Puppy reads `{puppy_home}/auth.yaml` and writes it to `~/PackUploader/auth.json` before each worker run.
* **Hard Block:** If `auth.yaml` does not exist or is not listed in `{puppy_home}/.gitignore`, Puppy exits immediately.

### **6.2 Pre-Flight & Worker Hygiene**
* **Dependency Check:** Verifies `git`, `node`, and `npm` are in PATH.
* **Worker Reset:** Runs `git reset --hard HEAD` and `git clean -fd` in `~/PackUploader/` before each run.
* **Settings Patch:** Sets `ewan: false` in `~/PackUploader/settings.json` after reset (the repo default enables ewanhowell.com-specific behaviour that is not applicable outside that context).
* **NPM Install:** If `~/PackUploader/node_modules/` is missing, runs `npm install` automatically.
* **Worker invocation:** `node --no-warnings scripts/{action}.js` run from `~/PackUploader/`.

### **6.3 Multi-Project Iteration**
Batch mode iterates projects listed under `projects:` in the global `puppy.yaml` sequentially. If only `pack:` or `name:` is present (flat single-project mode), the parent of the Puppy Home is used as the sole project.

### **6.4 State Harvesting**
After `import` or `create`, platform IDs, slugs, and full metadata are written back to the project's `puppy.yaml`. Images and their metadata are written to `{project_root}/puppy/images/` and `{project_root}/puppy/images/images.yaml` respectively. Leading and trailing underscores are stripped from image filenames on harvest.

### **6.5 Artifact Match**
Version must be the last component before `.zip`, separated by `-`, `_`, or `.` (e.g. `mypack-1.2.zip`, `pack-1.2.zip`). The filename need not start with the project slug. Strict boundary check ensures `1.2` does not match `1.2.4`.

### **6.7 Neutral Pack Metadata**
Certain properties are intrinsic to the pack and should not need to be repeated under each site's config block. Puppy translates top-level neutral keys to each site's native representation when staging. A neutral key sets the *entire group* of related per-site fields — for example, `resolution: 16` sets all Modrinth resolution tier tags (only `16x` true, all others false), sets CF `mainCategory: 16x`, sets PMC `resolution: 16`, and adds `16x` and `16x16` to PMC tags. There is no need to specify these in the site blocks unless overriding.

| Neutral key | CurseForge | Modrinth | PMC |
|---|---|---|---|
| `license: CC-BY-4.0` (SPDX) | `license: CC-BY 4.0` (last hyphen → space) | `license: CC-BY-4.0` (SPDX unchanged) | ignored |
| `resolution: 16` | `mainCategory: 16x` | full tier group (`16x: true`, others false) | `resolution: 16`, tags `16x` and `16x16` |
| `progress: 100` | ignored | ignored | `progress: 100` |
| `donation: {patreon: url, kofi: url, …}` | first entry as `{type: platform, value: url}` | full dict passed through | ignored |

Per-site overrides in `curseforge:`, `modrinth:`, `planetminecraft:` blocks take precedence over neutral keys — explicit per-site values are never overwritten. Site-specific fields with no neutral equivalent (e.g. CF `additionalCategories`, PMC `modifies`, PMC `tags`) should list all options explicitly so intent is clear.

### **6.6 Translation & Shielding**
* **Cross-Linking:** Puppy pre-scans all sibling projects in `puppy_home`, injecting a `projects` dict into the Jinja context. Each entry is keyed by `pack` slug and contains per-site sub-objects (e.g. `{{ projects.other.modrinth.url }}`). URLs are built from `slug` if available, falling back to `id`. The Modrinth URL path segment defaults to `mod`; set `modrinth.type:` (e.g. `resourcepack`, `modpack`) to override.
* **Site-Neutral Shorthand:** On any object in the Jinja context whose keys are site names (`curseforge`, `modrinth`, `planetminecraft`), omitting the site name resolves to the value for the site currently being rendered, or the empty string if that site has no value. For example, `{{ projects.other.url }}` in a description rendered for Modrinth resolves to `{{ projects.other.modrinth.url }}`. This generalises to any site-keyed attribute — not just `url`.
* **Shielding:** `md_html_tags` in `puppy.yaml` (default `['u']`) lists HTML tags to be protected from Markdown translation and mapped to target-site equivalents (e.g. `<u>` → `[u]` for PMC).

---

## Appendix A: Pack Family Setup

A "pack family" is a group of related packs managed together under one Puppy Home. They share auth, global config, and can cross-link to each other.

### Directory Layout

```
~/neon/
└── puppy/                          ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore
    ├── puppy.yaml                  ← shared config + projects list
    ├── modrinth/
    │   └── puppy.yaml              ← shared Modrinth overrides (discord link etc.)
    ├── NeonGlow/                   ← Project Root: main pack
    │   └── puppy/
    │       ├── puppy.yaml
    │       ├── description.md
    │       ├── icon.png
    │       ├── thumbnail.png
    │       ├── neonglow-2.1.zip
    │       └── images/
    │           ├── images.yaml
    │           └── screenshot1.png
    └── DarkNeon/                   ← Project Root: dark variant
        ├── screenshots/            ← images outside puppy/, referenced via source:
        │   └── screenshot1.png
        └── puppy/
            ├── puppy.yaml
            ├── description.md
            ├── icon.png
            ├── thumbnail.png
            ├── darkneon-2.1.zip
            └── images.yaml         ← flat format; source: ../screenshots
```

### Global `puppy.yaml`

```yaml
projects:
  - NeonGlow
  - DarkNeon

# Shared across all family members
license: CC-BY-4.0
resolution: 16

modrinth:
  discord: https://discord.gg/yourserver
```

### Per-Project `puppy.yaml`

Each project sets its own name, IDs, and any values that differ from the family defaults:

```yaml
# NeonGlow/puppy/puppy.yaml
name: NeonGlow
version: '2.1'

curseforge:
  id: 123456
  slug: neonglow
modrinth:
  id: AbCdEfGh
  slug: neonglow
  type: resourcepack
planetminecraft:
  id: 1234567
  slug: neonglow-texture-pack
```

```yaml
# DarkNeon/puppy/puppy.yaml
name: DarkNeon
version: '2.1'

curseforge:
  id: 234567
  slug: darkneon
modrinth:
  id: BcDeFgHi
  slug: darkneon
  type: resourcepack
planetminecraft:
  id: 2345678
  slug: darkneon-texture-pack
```

### Cross-Linking Between Family Members

Because all projects share the same Puppy Home, their URLs are available as Jinja variables in every description. Use `{{ projects.neonglow.url }}` in a shared `description.md` to link to the current site's URL automatically, or spell out the site explicitly when you need a specific one:

```markdown
# DarkNeon

The dark-mode companion to [NeonGlow]({{ projects.neonglow.url }}).
```

That single link renders as the correct URL for whichever site the description is being staged for. To hard-code a specific site:

```markdown
Also available on [CurseForge]({{ projects.neonglow.curseforge.url }}).
```

And from NeonGlow's description:

```markdown
Looking for a darker palette? Check out [DarkNeon]({{ projects.darkneon.url }}).
```

### Shared Description Content

A `description.md` at the Puppy Home level acts as a fallback for any project that doesn't have its own — useful for a shared footer or boilerplate:

```
~/neon/puppy/description.md   ← used by any project with no description.md of its own
```

Project-level descriptions take priority (see section 5.2 cascade).

### Running the Family

```
puppy push -n           # dry-run both packs
puppy push              # publish both
puppy push -s modrinth  # publish both, Modrinth only
```

---

## Appendix B: Planet Minecraft BBCode Dialect

Planet Minecraft uses a custom BBCode dialect that differs from standard forum BBCode. This appendix documents all supported tags, primarily as a reference for people authoring `.bbcode` description files by hand.

### Headings

```
[h1]Page Title[/h1]
[h2]Section[/h2]
[h3]Subsection[/h3]
```

`[h1]` through `[h6]` are supported. PMC renders each as a styled heading with a horizontal rule beneath.

### Inline Formatting

| Tag | Output | Notes |
|---|---|---|
| `[b]text[/b]` | **bold** | |
| `[i]text[/i]` | *italic* | |
| `[u]text[/u]` | underline | |
| `[s]text[/s]` | ~~strikethrough~~ | |
| `[color=#rrggbb]text[/color]` | coloured text | Hex colour only |
| `[size=Npx]text[/size]` | sized text | e.g. `24px` |
| `[bgcolor=#rrggbb]text[/bgcolor]` | background highlight | Hex colour only |
| `[style b color=#rrggbb]text[/style]` | composite style | Any combination of `b`, `i`, `u`, `color=` |

### Links and Images

```
[url=https://example.com]Link text[/url]
[img]https://example.com/image.png[/img]
[img=Alt text]https://example.com/image.png[/img]
```

PMC wraps outbound links in an internal tracking path (`/account/manage/texture-packs/{id}/example.com`). Puppy strips this back to the bare URL when rendering preview HTML.

### Block Elements

```
[quote]Quoted text[/quote]
[code]preformatted text[/code]
[hr]
```

`[hr]` is a void element (no closing tag required).

### Lists

PMC requires explicit `[/*]` terminators on each list item:

```
[list]
[*]First item[/*]
[*]Second item[/*]
[/list]
```

Ordered lists are not supported.

### Tables

Column widths are set on `[td]` with a `width` attribute (percentage or pixels):

```
[table]
[thead][tr][th]Header A[/th][th]Header B[/th][/tr][/thead]
[tbody]
[tr][td width=30%]Cell[/td][td]Cell[/td][/tr]
[/tbody]
[/table]
```

Supported table tags: `[table]`, `[thead]`, `[tbody]`, `[tr]`, `[th]`, `[td]`, `[td width=]`.

### Spoilers

```
[spoiler=Label text]Hidden content[/spoiler]
```

Renders as a collapsible block. The label argument is required.

### Markdown Conversion

When a description is written in Markdown, Puppy converts it to PMC BBCode automatically. The mapping is:

| Markdown | BBCode |
|---|---|
| `# Heading` | `[h1]Heading[/h1]` |
| `**bold**` | `[b]bold[/b]` |
| `*italic*` | `[i]italic[/i]` |
| `` `code` `` | `[icode]code[/icode]` |
| `![alt](url)` | `[img=alt]url[/img]` |
| `[text](url)` | `[url=url]text[/url]` |
| `* item` | `[list][*]item[/*][/list]` |
| `> quote` | `[QUOTE]quote[/QUOTE]` | uppercase tag |
| ` ```fenced``` ` | `[CODE]fenced[/CODE]` | uppercase tag |
| Soft line break | space (not `\n`) | |