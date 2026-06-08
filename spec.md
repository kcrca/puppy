# Puppy Design Specification

If you have a Minecraft project — a texture pack, mod, world, or other — keeping it nicely published on the major platforms is a significant job.
The three major sites are [CurseForge](https://www.curseforge.com/), [Modrinth](https://modrinth.com/), and [Planet Minecraft](https://www.planetminecraft.com/).
Keeping descriptions, images, captions, and the project itself up to date in three places with three different languages (html, markdown, and bbcode) and structures... not so much fun.

Puppy is designed to address these problems.
It also simplifies some other things along the way.

## Terminology

Puppy supports multiple project types; the `project_type` field in `puppy.yaml` declares what kind each project is (default: `pack`).
Sites that do not support the current project type are silently skipped.
CurseForge and PMC support `pack` and `world`; CurseForge and Modrinth support `mod`; Modrinth supports `pack`.
Modrinth does not yet have a world project type (as of mid-2026); world support is in `_MR_TYPE_MAP` for when it ships.
Each project is published across multiple sites.
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
* **`pull`:** Pulls live site data.
  Update yaml in puppy home and the project home (if different).
  Does **not** create description templates (those are created by `init`).
  Requires `id` in each site's config block; for PMC, also requires `slug` since there is no API to look it up from the ID.
  Per-site errors do not abort the other sites.
  Description body text pulled varies by platform:
  * *Modrinth:* Full description body pulled via API. This md file is put in the site home.
  * *CurseForge:* Full HTML description pulled via `api.curseforge.com/v1/mods/{id}/description` using the API token. Saved to `curseforge/description.html`.
  * *Planet Minecraft:* No description pulled. Manually paste content into `puppy/planetminecraft/description.bbcode`.
* **`create`:** Creates the pack project on each site, then automatically runs `pull` to harvest the site-assigned ID, slug, and any defaults back into `puppy.yaml`.
  Prompts for confirmation unless `-f/--force` is given.
  Per-site errors do not abort the other sites.

### Options & Flags
* **`-n/--dry-run`:** Valid for `push`.
  Executes the full pipeline without hitting APIs.
  Writes a per-site preview to `{tempdir}/puppy/{pack}/index.html` — a tabbed HTML page showing rendered descriptions, project metadata, icon, and images for each site.
  Also writes per-site description files to `{tempdir}/puppy/{pack}/{site}/description.{ext}`.
  For sites whose native format is not Markdown but whose source is Markdown (e.g. CurseForge, Planet Minecraft), also writes `description.md` alongside the native file.
  Prints the `file://` URL and opens it in the default browser automatically.
* **`--no-open`:** Suppress the automatic browser open after a dry run.
* **`-q/--quiet`:** Suppress progress output (default is verbose).
* **`-d/--dir [path]`:** Sets working directory. Defaults to CWD.
* **`-s/--site [sitename]`:** Limits action to one or more sites.
  Accepts a single name or a comma-separated list (e.g. `modrinth`, `cf,mr`).
  Site abbreviations are accepted (`cf`, `mr`, `pmc`).
  When omitted, defaults to the `sites:` list in `puppy.yaml` if present, otherwise all three sites.
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
* **`-I/--images`:** Controls image gallery handling.
  For `push`: include the image gallery in the upload (default: no images).
  For `pull`: download the image gallery and icon (`pack.png`) from the site.
  Without this flag on pull, images and icon are downloaded automatically only on first pull (when no image info is present); subsequent pulls leave existing image info untouched.
  When images are downloaded on pull, files go to `images/` and metadata to `images/images.yaml`; any top-level `images.yaml` is removed.
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

Structure:
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

**`sites:`** — optional list of site names (or abbreviations) that this project publishes to.
When present, commands that do not have an explicit `--site` flag operate only on the listed sites.
When absent, all sites that support the project's `project_type` are used.
Can be set at the Puppy Home level to apply to all projects, or per-project to override.
Example: `sites: [cf, mr]`

**Standard config fields:**
* `summary` — one-line project description shown in search results
* `optifine: true/false` — whether the pack requires [OptiFine](https://optifine.net/) (default false)
* `video: <youtube-id>` — a youtube ID for an associated video (default none)
* `links:` — external URLs for the project (all optional):
  * `home: <url>` — project home page; maps to CF social `website` and PMC `website.link`
  * `source: <url>` — source repository; maps to CF source link and Modrinth `source_url`
  * `issues: <url>` — issue tracker; maps to Modrinth `issues_url`. CurseForge has no separate issues URL field — it derives issues from the source URL automatically.
  * `patreon: <url>`, `kofi: <url>`, `paypal: <url>`, `buyMeACoffee: <url>`, `github_sponsors: <url>`, `other: <url>` — donation links;
    CF receives the first one as `{type, value}`;
    Modrinth receives all as `donation.*` (with `github_sponsors` mapped to `github`)
* `socials:` — social media accounts for the project (all optional):
  * `discord: <url>` — Discord server invite; maps to CF social `discord` and Modrinth `discord_url`
  * `mastodon/twitter/youtube/twitch/reddit/github/bluesky/…: <url>` — other social accounts; maps to CF social links (PMC and Modrinth have no equivalent for these)
  Per-site overrides (`curseforge.socials.*`, `modrinth.discord`) take precedence over neutral `socials`.
* `after_push: <message>` — a message printed to stdout after all projects have been pushed (not during dry-run).
  When set inside a site block, prints only when that site is active, prefixed with the site label.
  Useful for reminders about manual steps that can't be automated (e.g. fixing a PMC download link).

**Special image files** (placed in `{{project}}`):
* `pack.png` — the pack icon/avatar shown in site listings.
  Saved here by `pull` (when no icon PNG is already present).
  If absent, the icon is auto-discovered as the single `.png` in the project dir (see Asset Discovery below).
* `banner.png` — "Project Thumbnail": a large hero/featured image displayed separately from the gallery.
  Not part of the regular gallery upload.
  Override with `banner: <path>` in `puppy.yaml` to point at an external file instead of copying.
* `logo.png` — project logo; displayed at fixed aspect ratio (1280×256).
  Override with `logo: <path>` in `puppy.yaml` to point at an external file.

**Image entry flags** (in `images.yaml`):
* `featured: true` — image is promoted as a featured/highlighted gallery image on supporting sites

### Referencing Gallery Images in Descriptions

When `-I/--images` is active on `push`, puppy uploads gallery images to each site **before** rendering descriptions, so CDN URLs are available as Jinja variables.
Two helpers are injected into the template context:

* **`images`** — a mapping from image name (stem without extension) to CDN URL for that site.
  `{{ images.banner }}` → the CDN URL of `banner.jpg`/`banner.png` after upload.
  Returns `''` for unknown names (no error).

* **`img(name)`** — emits site-appropriate markup for the named image:
  * CurseForge / Modrinth: `<img src="…" width="600" alt="…"><br>`
  * Planet Minecraft: `[img width=600]…[/img]`
  Returns `''` if the name is not in the uploaded set.

Example (description.md):
```markdown
{{ img('banner') }}

Here is a closer look:

{{ img('screenshot1') }}
```

The same source file works on all three sites — each renders the correct markup for its platform.
When running without `-I`, `images.*` returns `''` for every name and `img()` returns `''`, so descriptions render cleanly in dry-run and text-only pushes.

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
* **Hard Block:** If `auth.yaml` does not exist or is not listed in `{{puppy}}/.gitignore`, Puppy exits immediately.

### Multi-Project Iteration
If there is a `projects` field in {{puppy}}/puppy.yaml, puppy iterates through these sequentially, unless specific projects are given on the command line.

### State Harvesting
After `pull` (and after the implicit pull that follows `create`), platform IDs, slugs, and full metadata are written back to the project's `puppy.yaml`.
If pulled, images and their metadata are written to `{{project}}/images/` and `{{project}}/images/images.yaml` respectively.
Leading and trailing underscores are stripped from image filenames on harvest.

### Artifact Match
In the name of the pack file, version must be the last component before `.zip`, separated by `-`, `_`, or `.` (e.g. `mypack-1.2.zip`, `pack-1.2.zip`).
The filename need not start with the project slug.
Strict boundary check ensures `1.2` does not match `1.2.4`.

### Neutral Project Metadata
Certain properties are intrinsic to the project and should not need to be repeated under each site's config block.
Puppy translates top-level neutral keys to each site's native representation when staging.
A neutral key sets the *entire group* of related per-site fields:
For example, `resolution: 16` sets the Modrinth resolution tier tags `16x` to true, all others false, sets CF `category: 16x`, sets PMC `resolution: 16`, and adds `16x` and `16x16` to PMC tags.
There is no need to specify these in the site blocks unless overriding.
Per-site overrides in `curseforge`, `modrinth`, `planetminecraft` blocks overwrite values set from neutral keys — explicit per-site values are never overwritten.
Site-specific fields with no neutral equivalent (e.g. CF `category`, PMC `modifies`, PMC `tags`, PMC `alt_download`) should list all options explicitly so intent is clear.
`planetminecraft.alt_download` sets the external download URL shown on PMC (PMC-specific because CF and Modrinth host files themselves).
`curseforge.category` accepts a single name or a list; the first becomes `primaryCategoryId`, the rest become `subCategoryIds`.
Named pack categories: `16x`, `32x`, `64x`, `128x`, `256x`, `512x and Higher`, `Data Packs`, `Font Packs`.
Named world categories: `Adventure`, `Creation`, `Game Map`, `Parkour`, `Puzzle`, `Survival`, `Modded World`.
Named mod categories: `Adventure and RPG`, `API and Library`, `Armor, Tools, and Weapons`, `Automation`, `Biomes`, `Bug Fixes`, `Cosmetic`, `Dimensions`, `Education`, `Energy`, `Energy, Fluid, and Item Transport`, `Farming`, `Food`, `Genetics`, `Magic`, `Map and Information`, `Miscellaneous`, `Mobs`, `Ores and Resources`, `Performance`, `Player Transport`, `Processing`, `Redstone`, `Server Utility`, `Skyblock`, `Storage`, `Structures`, `Technology`, `Utility & QoL`, `World Gen`.
Modrinth mod categories: `cursed`, `decoration`, `economy`, `equipment`, `food`, `game-mechanics`, `library`, `magic`, `management`, `minigame`, `mobs`, `optimization`, `technology`, `transportation`, `utility`, `social`, `storage`, `worldgen`.
Category names are case-insensitive.
A bare numeric ID is also accepted.

Examples:

| Neutral key | CurseForge | Modrinth | PMC |
|---|---|---|---|
| `project_type: pack/mod/world` | `classId: 12/6/17`; URL segment `texture-packs/mc-mods/worlds`; default category per type (override with `curseforge.category`) | `project_type: resourcepack/mod/world` | `/texture-pack/` URL and pack form for `pack`; `/project/` URL and world form (no resolution or modifies) for `world` |
| `loaders: [fabric, forge, neoforge, quilt]` | resolved as game version IDs via CF API; added to version file upload | `loaders` on version upload | ignored |
| `title: <string>` | ignored | ignored | overrides `name` as displayed project title |
| `license: CC-BY-4.0` ([SPDX](https://spdx.org/licenses/)) | `license: CC-BY 4.0` (last hyphen → space) | `license: CC-BY-4.0` (SPDX unchanged) | ignored |
| `resolution: 16` | `category: 16x` | full tier group (`16x: true`, others false) | `resolution: 16`, tags `16x` and `16x16` |
| `progress: 100` | ignored | ignored | `progress: 100` |
| `bedrock: true` | ignored (Bedrock is a separate CF site) | ignored (no Bedrock loader on MR) | pack: selects "Minecraft Bedrock" in version dropdown; world: checks "Bedrock Edition Map" |
| `links.home: <url>` | `socials.website` | ignored | `website.link` |
| `links.source: <url>` | source repo link | `source_url` | ignored |
| `links.patreon/kofi/… (donation keys)` | first key as `{type: platform, value: url}` | all donation keys passed as `donation.*` (`github_sponsors` → `github`) | ignored |
| `socials.discord: <url>` | `socials.discord` | `discord_url` | ignored |
| `socials.twitter/mastodon/… (other social keys)` | `socials.*` (CF social link types only) | ignored | ignored |
| `client_side: required/optional/unsupported` | adds game version ID 9638 (client env) if `required` or `optional` | `client_side` on project (create and update) | ignored |
| `server_side: required/optional/unsupported` | adds game version ID 9639 (server env) if `required` or `optional` | `server_side` on project (create and update) | ignored |

Each project type declares which neutral fields are valid for it.
Setting a field that does not apply to the declared type prints a warning and ignores it.
`client_side`, `server_side`, and `loaders` are valid only for `mod`.
`resolution` is valid only for `pack`.
`progress` is valid for `pack` and `world`.
CF encodes client/server environment as special entries in its game version ID list, not as separate API fields.
For resource packs and worlds, MR defaults to `['minecraft']` for the version loader and CF adds no loader IDs.


### Translation & Shielding
* **Cross-Linking:** Puppy pre-scans all sibling projects in `puppy_home`, injecting a `projects` dict into the Jinja context.
  Each entry is keyed by `pack` slug and contains per-site sub-objects (e.g. `{{ projects.other.modrinth.url }}`).
  URLs are built from `slug` if available, falling back to `id`.
  The Modrinth URL path segment is derived from `project_type` (e.g. `pack` → `resourcepack`, `mod` → `mod`, `modpack` → `modpack`).
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

