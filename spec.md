# Puppy Design Specification

If you have a texture or resource pack, keeping it nicely published on the major platforms is a significant job.
Currently there are three major sites for packs: [CurseForge](https://www.curseforge.com/), [Modrinth](https://modrinth.com/), and [Planet Minecraft](https://www.planetminecraft.com/).
Keeping descriptions, images, captions, and the pack itself up to date in three places with three different languages (html, markdown, and bbcode) and structures... not so much fun.

Currently there is one tool that manages this for you, [PackUploader](https://github.com/ewanhowell5195/PackUploader).
PackUploader uses APIs when they exist, and web protocols where they don't.
It handles a whole bunch of things automatically and nicely, but it has some downsides that are non-trivial to me.

* Your project's publishing information is not stored with your pack, but inside PackUploader's own source, intermixing its own implementation and your project data.
* Because of this, your information is not version controlled along with your pack (I'm assuming your pack is in git or some other VCS system).
* Each site has its own source language, so to avoid duplication, your description has to be in variables or other files and included via templates into the three different languages.
  For example, you can't just put in a link, you have put the url in a JSON file, and express it as a link in the three different languages.
  Only text and a few font styles are portable.

Puppy is designed to address these problems.
It also simplifies some other things along the way.

## Terminology

Currently puppy supports only packs, though projects of other types may be supported later.
Each pack is a project that is supported across multiple sites.
Typically this doc uses the term "project" except where talking about a pack in relation to its uploading and management, but not strictly.
Currently the sites supported are CurseForge (also called "cf"), Modrinth, and Planet Minecraft (also called "pmc").

For the examples in this document, we will use a pack named "Neon".
Where examples require multiple packs (puppy allows multiple packs in the same repo), the second example pack will be named "Dark".
Examples will also use UNIX paths, though puppy works with Windows paths on Windows systems.

## Design Principles
* **User-Centric Simplicity:** Simple cases should be the simplest to express; obvious defaults will be used if they are unambiguous.
* **Implicit Discovery:** Asset discovery (icons, zips) is preferred over manual path mapping.
* **Integrated Versioning:** All data and harvested IDs reside in the project source directory.
* **Markdown-First:** Markdown is the preferred expression language for text, and is translated to other languages as required.
  Site-specific native files (`.html`, `.bbcode`) act as overrides if present.
* **Cross-Platform:** All paths and subprocesses must work on macOS, Linux, and Windows.

## Directory Architecture

For the `neon` pack that lives in your home directory (`~/neon`), the puppy-related data files are:

* **Global Home:** `~/neon/` (typically the root of a git or other VCS repo).
* **Puppy Home:** `~/neon/puppy/`
* **Auth & Gitignore:** `~/neon/puppy/auth.yaml`, `~/neon/puppy/.gitignore` that includes `auth.yaml`.
* **Global Config:** `~/neon/puppy/puppy.yaml`
* **Project Home:** For a single pack, Puppy Home (`~/neon/puppy/`) doubles as Project Home.
  For multiple packs, each has its own subdirectory: `~/neon/puppy/neon/`, `~/neon/puppy/dark/`.
* **Images:** `~/neon/puppy/images/` or `~/neon/puppy/images.yaml`
* **Dry Run Output:** `{tempdir}/puppy/{pack}/` (used for `--dry-run`, wiped fresh each run)
* **Worker Directory:** `~/PackUploader/` (the PackUploader repo — reset before each run; this can be overridden)

Site-specific data is global if it is in the global home, or project specific if it is in the project home.

## Information priority

Each project and site is handled individually within a run of puppy.
The information for a run has a priority order where it is found.

1. The project's site home (such as `~/neon/puppy/neon/pmc/puppy.yaml)
1. The project's home (such as `~/neon/puppy/neon/puppy.yaml)
1. Puppy's site home (such as `~/neon/puppy/pmc/puppy.yaml)
1. Puppy's home (such as `~/neon/puppy/puppy.yaml)

So if a single run of puppy talks to three sites about two packs, there will be six sets of information, built independently for each site interaction.

## Core Identity & Naming
* **`pack`** (internal slug): Lowercase alphanumeric only, spaces and special characters stripped.
  Derived from the directory name unless overridden.
  Example: `'Neon Glow!'` → `neonglow`.
* **`name`** (display name): Preserves casing and special characters exactly (`'Neon Glow!'` stays `'Neon Glow!'`).
  If the source string is strictly lowercase ASCII, converts to title case (`neon` → `Neon`).
* **Single override:** If only `name` is provided, `pack` is derived by slugifying `name` (lowercase, strip non-alphanumerics).
  If only `pack` is provided, `name` is derived by the same casing rules.
  Both can be set explicitly.
* **Auto-update:** Whenever a project is loaded for any action, if either `name` or `pack` was absent from `puppy.yaml`, the derived value is written back automatically.

Puppy is a thin management layer for `PackUploader`.
It handles staging, factory-resetting the worker, and dependency checks automatically.
It then copies out any updates required into the puppy tree.

### Running Location
For simplicity, puppy can be invoked from:
* **Global Home** (`~/neon/`) — detected by presence of `puppy/auth.yaml`
* **Puppy Home** (`~/neon/puppy/`) or anywhere underneath it — detected by presence of `auth.yaml`

All relative paths named within yaml files are derived relative to that file's location, not the running location.

## CLI & Actions
`puppy [options] [action] [project ...]`

### Actions
Puppy has the following actions:

* **`init`:** Creates four files in `puppy/`: `auth.yaml`, `.gitignore`, `puppy.yaml`, and `description.md`.
  Derives `name` and `pack` from the directory name.
  Any file that already exists is left untouched with a warning.
  `puppy.yaml` is pre-populated with skeleton site entries; `description.md` contains a short comment.
* **`push`** (Default): Updates metadata, summaries, descriptions, images, and icons.
  With `-p/--pack`, also uploads the zip artifact.
  Requires `version` in `puppy.yaml` or `-V/--version` when using `-p`.
* **`import`:** Pulls live site data.
  Update yaml in puppy home and the project home (if different).
  Does **not** create description templates (those are created by `init`).
  Requires `id` in each site's config block; for PMC, also requires `slug` since there is no API to look it up from the ID.
  Per-site errors do not abort the other sites.
  Description body text import varies by platform:
  * *Modrinth:* Full description body imported via API. This md file is put in the site home.
  * *CurseForge:* Full HTML description imported via `api.curseforge.com/v1/mods/{id}/description` using the API token. Saved to `curseforge/description.html`.
  * *Planet Minecraft:* No description imported. Manually paste content into `puppy/planetminecraft/description.bbcode`.
* **`create`:** Creates the pack project on each site, then automatically runs `import` to harvest the site-assigned ID, slug, and any defaults back into `puppy.yaml`.
  Prompts for confirmation unless `-f/--force` is given.
  Per-site errors do not abort the other sites.
* **`clean`:** Resets the PackUploader worker without pushing.

### Options & Flags
* **`-n/--dry-run`:** Valid for `push`.
  Executes the full pipeline without hitting APIs or running the worker.
  Writes a per-site preview to `{tempdir}/puppy/{pack}/index.html` — a tabbed HTML page showing rendered descriptions, project metadata, icon, and images for each site.
  Prints the `file://` URL and opens it in the default browser automatically.
* **`--no-open`:** Suppress the automatic browser open after a dry run.
* **`-v` / `-vv`:** High-level progress (`-v`) or raw worker stdout/stderr (`-vv`).
* **`-d/--dir [path]`:** Sets working directory. Defaults to CWD.
* **`-s/--site [sitename]`:** Limits action to one or more sites.
  Accepts a single name or a comma-separated list (e.g. `modrinth`, `cf,mr`).
  Site abbreviations are accepted (`cf`, `mr`, `pmc`).
* **`-V/--version [string]`:** Version string override.
  Falls back to `version` in `puppy.yaml`.
  Artifact matched via any `.zip` in `puppy/` whose filename ends with `[-_.]version.zip`.
* **`-p/--pack`:** Valid for `push`.
  Include zip artifact upload in `push`.
  Requires `minecraft` or `versions` in `puppy.yaml`.
  Upload is skipped per-site if the artifact is already current:
  * **Modrinth:** Compares SHA-512 hash of local zip against the hash stored in the latest version's file listing.
  * **CurseForge:** Compares both version string and file size (bytes) against the most recent uploaded file; uploads if either differs.
  * **Planet Minecraft:** Compares version string against last version recorded in `puppy/.publish_state.yaml`.
* **`-f/--force`:** Valid for `push` and `create`.
  With `push -p`, bypasses skip logic and uploads unconditionally on all sites.
  With `create`, skips the confirmation prompt.
* **`--worker [path]`:** PackUploader worker directory. Defaults to `~/PackUploader`.
* **`-I/--images`:** Controls image gallery handling.
  For `push`: include the image gallery in the upload (default: no images).
  For `import`: download the image gallery and icon (`pack.png`) from the site.
  Without this flag on import, images and icon are downloaded automatically only on first import (when no image info is present); subsequent imports leave existing image info untouched.
  When images are downloaded on import, files go to `images/` and metadata to `images/images.yaml`; any top-level `images.yaml` is removed.
  Icon is copied as `pack.png` only if no icon PNG is already present.
  CurseForge and Modrinth provide the icon; PMC does not.

### Arguments
* **`project ...`** (positional): Limits action to one or more projects, matched by pack slug.
  Example: `puppy push neon dark` will push only those two projects in a multi-project repo.

## Known Sites

Currently there are three known sites:

CurseForge: Abbreviation: "cf", native language: HTML (`.html`)
Modrinth: native language: Markdown (`.md`)
Planet Minecraft: Abbreviation: "pmc", native language: variant of BBCode (`.bbcode`)

## Cascading Configuration & Discovery

The four config layers are merged in priority order (lowest first).
Dicts merge additively — keys present in a higher-priority layer are added or overwrite individual keys; the entire dict is not replaced.
Everything else (strings, numbers, booleans, lists) overwrites.


### auth.yaml
`auth.yaml` stores API credentials and must never be committed.
Puppy exits with a fatal error if `auth.yaml` does not exist or is not listed in `puppy/.gitignore`.

Structure mirrors PackUploader's `auth.json`:
```yaml
curseforge:
  token: ...
  cookie: CobaltSession=...
modrinth: <token>
planetminecraft: pmc_autologin=<cookie>
```

### minecraft: shorthand
In puppy.yaml, `minecraft` sets the Minecraft game version for artifact uploads across all sites.
A string value is treated as an exact version (`minecraft: '26.1'` → `type: exact, version: '26.1'`).
A dict value is used as-is (`minecraft: {type: latest}`).
Required when using `push --pack` unless `versions` is fully specified.

## Template Expansion

Puppy resolves files by searching in the information priority order given above.
Within that, for a given site during template expansion, a file in the site's preferred language takes precedence over a markdown file.
In a site directory within a separate project directory (such as `~/neon/puppy/neon/pmc`) has both a language-specific variant (`foo.bbcode`) and a markdown variant (`foo.md`), a warning is given because the markdown will never be used.

The description for a site is provided in a `description` file found in this way.
Description files and YAML string values are rendered as [Jinja2](https://jinja.palletsprojects.com/) templates.
All config keys from `puppy.yaml` are available as variables: `{{ version }}`, `{{ name }}`, `{{ modrinth.slug }}` etc.
If `{{ foo }}` isn't a yaml property, then it is searched for as a file in the same way as `description.{ext}` is searched for, and if found, the file's contents are the value.
This allows large reusable blocks (for example `{{ credits }}` → `credits.md`).

Full Jinja2 syntax is supported (`{% if %}`, `{% for %}`, filters, etc.).
Unrecognised variables in `{{ }}` expressions raise an error; they are treated as falsy in `{% if %}` tests.
This process is repeated until no more Jinja2 directives remain.

Expansion uses a re-entrancy counter, incremented when any value expansion begins, decremented when it ends.
If it exceeds 100, that is an error; this prevents infinite recursion.

Two path variables are automatically injected into every Jinja context:
* `{{ top }}` — absolute path to the parent of puppy's home (`~/neon`)
* `{{ puppy }}` — absolute path to puppy's home (`~/neon/puppy`)
* `{{ project }}` — absolute path to the current project's home (`~/neon/puppy/NeonGlow`)

These can be used in `puppy.yaml` values as well as description templates — for example `icon: {{top}}/neon/pack.png`.

A `read()` function is also available in all Jinja contexts to inline the contents of any file by path:
`{{ read(top + "/shared/credits.md") }}`
All yaml values and path variables are available as arguments.

**Recursive config expansion:** String values in the config that contain `{{ }}` expressions are themselves expanded through Jinja — repeatedly until stable.
This means a config key can reference other config keys, projects variables, or file-inclusion variables, and those references will be fully resolved before they appear in the description.

**Standard config fields passed to the worker:**
* `summary` — one-line project description shown in search results
* `optifine: true/false` — whether the pack requires [OptiFine](https://optifine.net/) (default false)
* `video: <youtube-id>` — a youtube ID for an associated video (default none)
* `links:` — external URLs for the project (all optional):
  * `home: <url>` — project home page; maps to CF social `website` and PMC `website.link`
  * `source: <url>` — source repository; maps to `github` internally, which PU uses for CF source link and Modrinth `source_url`/`issues_url`
  * `issues: <url>` — issue tracker; stored but not yet applied (requires PU to expose a separate `issues_url` setting)
  * `patreon: <url>`, `kofi: <url>`, `paypal: <url>`, `buyMeACoffee: <url>`, `github_sponsors: <url>`, `other: <url>` — donation links;
    CF receives the first one as `{type, value}`;
    Modrinth receives all as `donation.*` (with `github_sponsors` mapped to `github`)
* `after_push: <message>` — a message printed to stdout after all projects have been pushed (not during dry-run).
  When set inside a site block, prints only when that site is active, prefixed with the site label.
  Useful for reminders about manual steps that can't be automated (e.g. fixing a PMC download link).

**Special image files** (placed in `{{project}}`):
* `pack.png` — the pack icon/avatar shown in site listings.
  Saved here by `import` (when no icon PNG is already present).
  If absent, the icon is auto-discovered as the single `.png` in the project dir (see Asset Discovery below).
* `banner.png` — "Project Thumbnail": a large hero/featured image displayed separately from the gallery.
  Not part of the regular gallery upload.
  Override with `banner: <path>` in `puppy.yaml` to point at an external file instead of copying.
* `logo.png` — project logo; displayed at fixed aspect ratio (1280×256).
  Override with `logo: <path>` in `puppy.yaml` to point at an external file.

**Image entry flags** (in `images.yaml`):
* `embed: true` — image is embedded in the description body
* `featured: true` — image is promoted as a featured/highlighted gallery image on supporting sites

### Path Resolution Rules
* **Internal Files:** Follow the file cascade (section 5.2).
* **External Files:** Paths outside `puppy/` are treated as literal — no extension guessing or hierarchy search.
* **Relative Paths:** All relative paths in any YAML file are resolved relative to the containing file. (This is where `{{top}}`, `{{puppy}}`, and `{{project}}` come in handy.)

### Asset Discovery
For `create` and `push`, the icon and zip artifact are resolved as follows:
* **Explicit paths** `icon` and `zip` in `puppy.yaml`
* **Implicit discovery** (fallback): a single `.png` in the project's home (excluding `banner.png` and `logo.png`) is the icon; a single `.zip` is the artifact. Multiple files of either type is a fatal error.
* **Icon validation:** The icon must be a square PNG.

### Image Metadata
Image metadata (the list of images with names, descriptions, and file references) lives in one of two locations — both are valid, but not both simultaneously:
* **`images.yaml`** — used when images live outside the puppy directory (referenced via `source`).
* **`images/images.yaml`** — used when image files are stored inside `puppy/images/`.

The image directory is found searching in the standard order.

Both formats support an optional top-level `source` key pointing to a directory (resolved relative to the containing file) where image files are found.
If `source` is absent, images are loaded from `puppy/images/`.

**Image format handling:** The `file` field may include or omit a file extension.
If omitted, and there is a .png file, it is used.
Otherwise, puppy searches for any file with a recognised image extension (`.jpg`, `.jpeg`, `.webp`, `.gif`, etc.), and converts it to PNG while staging, since that is always accepted.
If the file cannot be found or converted, Puppy exits with an error.

## Operational Logic

### Security & Auth Protocol
* Puppy reads `{{puppy}}/auth.yaml` and writes it to `~/PackUploader/auth.json` before each worker run.
* **Hard Block:** If `auth.yaml` does not exist or is not listed in `{{puppy}}/.gitignore`, Puppy exits immediately.

### Pre-Flight & Worker Hygiene
* **Dependency Check:** Verifies `git`, `node`, and `npm` are in PATH.
* **Worker Reset:** Runs `git reset --hard HEAD` and `git clean -fd` in `~/PackUploader/` before each run.
* **Settings Patch:** Sets `ewan: false` in `~/PackUploader/settings.json` after reset (the repo default enables ewanhowell.com-specific behaviour that is not applicable outside that context).
* **NPM Install:** If `~/PackUploader/node_modules/` is missing, runs `npm install` automatically.
* **Worker invocation:** `node --no-warnings scripts/{action}.js` run from `~/PackUploader/`.

### Multi-Project Iteration
If there is a `projects` field in {{puppy}}/puppy.yaml, puppy iterates through these sequentially, unless specific projects are given on the command line.

### State Harvesting
After `import` (and after the implicit import that follows `create`), platform IDs, slugs, and full metadata are written back to the project's `puppy.yaml`.
If imported, images and their metadata are written to `{{project}}/images/` and `{{project}}/images/images.yaml` respectively.
Leading and trailing underscores are stripped from image filenames on harvest.

### Artifact Match
In the name of the pack file, version must be the last component before `.zip`, separated by `-`, `_`, or `.` (e.g. `mypack-1.2.zip`, `pack-1.2.zip`).
The filename need not start with the project slug.
Strict boundary check ensures `1.2` does not match `1.2.4`.

### Neutral Pack Metadata
Certain properties are intrinsic to the pack and should not need to be repeated under each site's config block.
Puppy translates top-level neutral keys to each site's native representation when staging.
A neutral key sets the *entire group* of related per-site fields:
For example, `resolution: 16` sets the Modrinth resolution tier tags `16x` to true, all others false, sets CF `mainCategory: 16x`, sets PMC `resolution: 16`, and adds `16x` and `16x16` to PMC tags.
There is no need to specify these in the site blocks unless overriding.
Per-site overrides in `curseforge`, `modrinth`, `planetminecraft` blocks overwrite values set from neutral keys — explicit per-site values are never overwritten.
Site-specific fields with no neutral equivalent (e.g. CF `additionalCategories`, PMC `modifies`, PMC `tags`) should list all options explicitly so intent is clear.

Examples:

| Neutral key | CurseForge | Modrinth | PMC |
|---|---|---|---|
| `license: CC-BY-4.0` ([SPDX](https://spdx.org/licenses/)) | `license: CC-BY 4.0` (last hyphen → space) | `license: CC-BY-4.0` (SPDX unchanged) | ignored |
| `resolution: 16` | `mainCategory: 16x` | full tier group (`16x: true`, others false) | `resolution: 16`, tags `16x` and `16x16` |
| `progress: 100` | ignored | ignored | `progress: 100` |
| `links.patreon/kofi/… (donation keys)` | first key as `{type: platform, value: url}` | all donation keys passed as `donation.*` (`github_sponsors` → `github`) | ignored |


### Translation & Shielding
* **Cross-Linking:** Puppy pre-scans all sibling projects in `puppy_home`, injecting a `projects` dict into the Jinja context.
  Each entry is keyed by `pack` slug and contains per-site sub-objects (e.g. `{{ projects.other.modrinth.url }}`).
  URLs are built from `slug` if available, falling back to `id`.
  The Modrinth URL path segment defaults to `mod`; set `modrinth.type` (e.g. `resourcepack`, `modpack`) to override.
* **External Projects (`linked_projects`):** Projects outside the current Puppy Home can be added to the `projects` context via `linked_projects` in the global `puppy.yaml`.
  Each entry follows the same per-site structure as a normal project.
  A top-level `slug` key serves as the default slug for all sites, overridden by any per-site `slug`.
  Example:
  ```yaml
  linked_projects:
    restworld:
      slug: restworld          # default for all sites
      planetminecraft:
        slug: restworld-123    # PMC uses a different slug
  ```
* **Site-Neutral Shorthand:** On any object in the Jinja context whose keys are site names (`curseforge`, `modrinth`, `planetminecraft`), omitting the site name resolves to the value for the site currently being rendered.
  For example, `{{ projects.other.url }}` in a description rendered for Modrinth resolves to `{{ projects.other.modrinth.url }}`.
  This generalises to any site-keyed attribute, not just `url`.
* **Shielding:** `md_html_tags` in `puppy.yaml` (default `['u']`) lists HTML tags to be protected from Markdown translation and mapped to target-site equivalents (e.g. `<u>` → `[u]` for PMC).

---

## Appendix A: Pack Family Setup

### Single-Pack Layout

For a single pack, `puppy init` creates:

```
~/neon/
└── puppy/                          ← Puppy Home = Project Home
    ├── auth.yaml                   ← credentials (never committed)
    ├── .gitignore
    ├── puppy.yaml                  ← config for this pack
    └── description.md              ← pack description
```

### Multi-Pack Layout

A "pack family" is a group of related packs managed together under one puppy home in a single repo.
They share auth, global config, and can cross-link to each other.

```
~/neon/
└── puppy/                          ← Puppy Home (auth.yaml, global config)
    ├── auth.yaml                   ← shared credentials (never committed)
    ├── .gitignore
    ├── puppy.yaml                  ← shared config + projects list
    ├── modrinth/
    │   └── puppy.yaml              ← shared Modrinth overrides (discord link etc.)
    ├── NeonGlow/                   ← Project Home: main pack
    │   ├── puppy.yaml
    │   ├── description.md
    │   ├── icon.png
    │   ├── banner.png
    │   ├── neonglow-2.1.zip
    │   └── images/
    │       ├── images.yaml
    │       └── screenshot1.png
    └── DarkNeon/                   ← Project Home: dark variant
        ├── screenshots/            ← images outside project home, referenced via source:
        │   └── screenshot1.png
        ├── puppy.yaml
        ├── description.md
        ├── icon.png
        ├── banner.png
        ├── darkneon-2.1.zip
        └── images.yaml             ← flat format; source: ../screenshots
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
# NeonGlow/puppy.yaml
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
# DarkNeon/puppy.yaml
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

Because all projects share the same Puppy Home, their URLs are available as Jinja variables in every description.
Use `{{ projects.neonglow.url }}` in a shared `description.md` to link to the current site's URL automatically, or spell out the site explicitly when you need a specific one:

```markdown
# DarkNeon

The dark-mode companion to [NeonGlow]({{ projects.neonglow.url }}).
```

That single link renders as the correct URL for whichever site the description is being staged for.
To hard-code a specific site:

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

Project-level descriptions take priority (see the cascade in the Template Expansion section).

### Running the Family

```
puppy push -n           # dry-run both packs
puppy push              # publish both
puppy push -s modrinth  # publish both, Modrinth only
```

---

## Appendix B: Planet Minecraft BBCode Dialect

Planet Minecraft uses a custom BBCode dialect that differs from standard forum BBCode.
This appendix documents all supported tags, primarily as a reference for people authoring `.bbcode` description files by hand.

### Headings

```
[h1]Page Title[/h1]
[h2]Section[/h2]
[h3]Subsection[/h3]
```

`[h1]` through `[h6]` are supported.
PMC renders each as a styled heading with a horizontal rule beneath.

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

PMC wraps outbound links in an internal tracking path (`/account/manage/texture-packs/{id}/example.com`).
Puppy strips this back to the bare URL when rendering preview HTML.

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

Renders as a collapsible block.
The label argument is required.

### Markdown Conversion

When a description is written in Markdown, Puppy converts it to PMC BBCode automatically.
The mapping is:

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

---

## Appendix C: How Puppy Uses PackUploader

Puppy implements its actions by staging data into a [PackUploader](https://github.com/ewanhowell5195/PackUploader) worker directory and invoking its scripts.
This appendix documents the interface between the two tools.

### Worker Directory Layout

Before each run puppy resets the worker (`git reset --hard HEAD && git clean -fd`) and writes:

```
~/PackUploader/
├── auth.json                       ← credentials, written from auth.yaml
├── settings.json                   ← patched to set ewan: false
├── data/
│   ├── details.json                ← push: {id, images, live}
│   ├── import.json                 ← import: per-site IDs and slugs
│   └── create.json                 ← create: name, summary, icon path
└── projects/
    └── {pack}/
        ├── project.json            ← full config + per-site IDs/slugs
        ├── pack.png                ← icon (always PNG, square)
        ├── banner.png           ← optional banner image
        ├── logo.png                ← optional logo
        ├── images/                 ← gallery images (always PNG)
        └── templates/
            ├── modrinth.md         ← rendered description + {{ images }}
            ├── curseforge.html
            └── planetminecraft.bbcode
```

### Description Templates

For each site, puppy writes `templates/{site}.{ext}` containing the rendered description body followed by `\n\n{{ images }}\n`.
The worker substitutes `{{ images }}` with the formatted image gallery before uploading.
If no description was found in the cascade, a minimal `{{ description }}\n\n{{ images }}\n` template is written instead.

### Scripts Invoked

| Action | Script |
|---|---|
| `push` | `scripts/details.js` |
| `import` | `scripts/import.js` |
| `create` | `scripts/create.js` |

All scripts are run as `node --no-warnings scripts/{action}.js` from the worker directory.

### Output

After each script run, puppy reads `projects/{pack}/project.json` back from the worker directory to harvest updated IDs, slugs, and metadata.
