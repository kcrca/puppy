# Spec: Puppy Native

Puppy publishes Minecraft projects (resource packs, world saves, mods) to multiple sites from a single config file.
This spec describes the fully-native version: all site API calls in Python, no Node.js or PackUploader.

---

## Design Principles

**Sites are self-contained.**
All knowledge about a site — API endpoints, auth mechanism, category maps, supported project types, description format — lives inside the site class.
No site-specific branching outside that class.

**Project types are data, not control flow.**
`type: mod` changes what a site sends (classId, loaders, file extension), but the push pipeline is the same.
Each site declares what types it supports and maps type → site-specific values.

**Adding a new site means: implement `Site`, register it.**
No other file needs editing.

**Adding a new project type means: one entry in `PROJECT_TYPES`, entries in each site's type map.**
The pipeline doesn't change.
`ProjectType` is a data record, not a protocol — type variation is data, not behavior.

---

## Module Map

```
puppy/
  cli.py          command-line parsing; calls runner
  runner.py       orchestrates actions across projects
  core.py         Project: name/slug derivation
  config.py       puppy.yaml loading, Jinja2 config synthesis
  sites/
    __init__.py   exports CURSEFORGE, MODRINTH, PMC, SITES list
    base.py       Site class, PushContext, PulledData, HTTP helpers
    curseforge.py CurseForgeSite
    modrinth.py   ModrinthSite
    pmc.py        PlanetMinecraftSite
  imaging.py      Pillow resize/encode for all asset types
  renderer.py     Jinja2 rendering; DescriptionFormat hierarchy (MD, HTML, BBCode)
  syncer.py       push pipeline: metadata + gallery sync per site
  publisher.py    release file upload (ZIP/JAR) per site
  puller.py       pull pipeline: download metadata/images from sites
  creator.py      create pipeline: register new projects on sites
  checks.py       preflight validation
  auth.py         AuthFlow protocol + per-site implementations; puppy auth command
  init.py         puppy init scaffolding
  errors.py       AuthExpiredError, SiteError
```

Adding a new site: create one file in `sites/`, register an instance in `sites/__init__.py`.
No other files need changing.

`pmc_browser.py` is an optional module installed with `puppy[pmc]`.
All other modules must import it conditionally.

---

## HTTP and Concurrency

Site HTTP calls use `urllib.request` (stdlib, no added dependency).
`syncer.py` runs the per-site push loop with `concurrent.futures.ThreadPoolExecutor` so CF, Modrinth, and PMC push in parallel.
Site methods stay synchronous — parallelism is at the call site, not inside site classes.

---

## `Site` Protocol

Every site is a class that implements this interface.
All methods have default no-op implementations in the base class so sites only override what they need.

```python
class Site:
    name: str           # canonical key: 'curseforge', 'modrinth', 'planetminecraft'
    aliases: list[str]  # shortcuts accepted by -s flag: ['cf'], ['mr'], ['pmc']
    label: str          # display name: 'CurseForge', 'Modrinth', 'Planet Minecraft'

    # ── Type support ──────────────────────────────────────────────────────────

    def supports(self, project_type: str) -> bool:
        """Return False to silently skip this site for the given project type."""
        return True

    # ── Push operations (called by syncer.py) ─────────────────────────────────

    def push_metadata(self, ctx: PushContext) -> None:
        """Update description, title, summary, links, license, categories."""

    def push_icon(self, ctx: PushContext) -> None:
        """Upload/replace project icon."""

    def push_gallery(self, ctx: PushContext) -> None:
        """Sync gallery: delete stale images, upload new ones."""

    def push_file(self, ctx: PushContext) -> None:
        """Upload release artifact (ZIP or JAR)."""

    def needs_upload(self, ctx: PushContext) -> bool:
        """Return False if this version is already present on the site."""
        return True

    # ── Pull (called by puller.py) ────────────────────────────────────────────

    def pull(self, ctx: PullContext) -> PulledData:
        """Return current metadata, icon URL, gallery URLs from the site."""

    # ── Project lifecycle (called by creator.py) ──────────────────────────────

    def create(self, ctx: PushContext) -> str:
        """Create a new project on the site. Returns the new project ID."""

    # ── Auth ──────────────────────────────────────────────────────────────────

    def auth_flow(self) -> AuthFlow:
        """Return the AuthFlow that knows how to obtain credentials for this site."""

    def validate_auth(self, auth: dict) -> None:
        """Raise AuthExpiredError if credentials are missing or obviously invalid."""

    # ── Description format ────────────────────────────────────────────────────

    description_format: DescriptionFormat = MD   # assign a format object

    def template_helpers(self, config: dict) -> dict:
        """Jinja2 context additions injected before rendering.
        Returned dict is merged into the template context.
        Use for site-specific URL builders and other per-site template functions.
        Example: {'project_url': lambda slug: f'https://modrinth.com/mod/{slug}'}
        Default: empty — no additional helpers."""
        return {}

    def description_postprocess(self, text: str) -> str:
        """Apply site-specific tweaks to the fully converted text.
        Runs after Jinja2 rendering and format conversion.
        Examples: strip unsupported tags, fix encoding edge cases.
        Default: identity."""
        return text

    # ── Site utility methods ───────────────────────────────────────────────────
    # These are genuinely site-specific but not push/pull operations.
    # Every site must implement them; they require no auth and make no API calls.

    def url_for(self, site_config: dict) -> str | None:
        """Return the public project URL, or None if not determinable.
        Used in dry-run output and after_push messages."""

    def resolve_id(self, config: dict, auth: dict) -> dict:
        """Resolve a slug to a numeric/string project ID if the site requires it.
        Returns updated config. Default: return config unchanged.
        Example: Modrinth accepts slug on the API but some calls need the opaque ID."""
        return config

    def puppy_yaml_entry(self, pack: str) -> str:
        """Return the YAML snippet written by `puppy init` for this site."""

    def auth_yaml_entry(self) -> str:
        """Return the auth.yaml snippet shown by `puppy auth` for manual fallback."""

    def preview_rows(self, site_config: dict) -> list[tuple[str, str]]:
        """Key-value pairs shown in the dry-run HTML preview for this site.
        Examples: category, license, resolution, tags."""
        return []
```

**Description conversion** is a format problem, not a site problem.
`DescriptionFormat` is a class hierarchy in `renderer.py`; sites reference a format object, they do not implement conversion.

```python
class DescriptionFormat:
    ext: str    # preferred local source file extension: '.md', '.html', '.bbcode'

    def convert(self, text: str, source_ext: str) -> str:
        """Convert text from source_ext to this format. Identity if same."""

class MarkdownFormat(DescriptionFormat):
    ext = '.md'

class HTMLFormat(DescriptionFormat):
    ext = '.html'
    def convert(self, text, source_ext):
        if source_ext == '.md': return md_to_html(text)
        ...

class BBCodeFormat(DescriptionFormat):
    ext = '.bbcode'
    def convert(self, text, source_ext):
        if source_ext == '.md': return md_to_bbcode(text)
        ...

MD     = MarkdownFormat()
HTML   = HTMLFormat()
BBCODE = BBCodeFormat()
```

Sites set `description_format` to one of these singletons:

```python
class CurseForgeSite(Site):
    description_format = HTML

class ModrinthSite(Site):
    description_format = MD

class PlanetMinecraftSite(Site):
    description_format = BBCODE
```

The push pipeline processes descriptions in three steps:

```python
# 1. Jinja2 rendering — site contributes helpers to the template context
context = {**config, **site.template_helpers(config)}
rendered = jinja2_render(source_text, context)

# 2. Format conversion — source format → site's target format
converted = site.description_format.convert(rendered, source_ext)

# 3. Site-specific postprocess — final-pass text manipulation
final = site.description_postprocess(converted)
```

`template_helpers` is for structured, site-aware substitutions in templates — e.g., `{{ project_url('fabric-api') }}` resolving to the correct URL for each site.
`description_postprocess` is for final-pass text manipulation that can't be done in templates — tag stripping, encoding fixes, etc.
Both are optional; defaults are identity/empty.

`project_url(slug)` resolution order:
1. `related:` entries in `puppy.yaml` — external projects; `type` required per entry.
2. Sibling projects in the same puppy home — `type` read from their own `puppy.yaml`.
3. If slug not found in either: raise a clear error naming the missing slug.

Sites use both the slug's `type` and the per-entry site ID to build the URL.
Example: `related.fabric-api.type = mod` + `related.fabric-api.modrinth = P7dR8mSH` → `https://modrinth.com/mod/P7dR8mSH`.

**CurseForge `descriptionType`:** The `_api/projects/description/{id}` endpoint takes `{ description: <string>, descriptionType: <int> }`.
PU sends `descriptionType: 1` for HTML.
CF added a Markdown editor to its dashboard in Feb 2026 but made no documented API change; a `descriptionType` value for Markdown may exist but is unknown without a DevTools sniff.
Use `descriptionType: 1` (HTML) until confirmed otherwise.

**Adding a new site with an existing format**: set `description_format = HTML`. Zero new code.
**Adding a new site with a new format**: add one `DescriptionFormat` subclass to `renderer.py`. No changes to `sites.py` or the pipeline.

**Registering a site:** Add an instance to `SITES` in `sites.py`.
`SiteVisitor` iterates `SITES`, filtered by the `-s` flag.
No other file needs changing.

---

## `ProjectType`

Project types have cross-cutting concerns that aren't site-specific: file extension, artifact finder strategy, required config keys.
These live in a central registry as a lightweight dataclass — not a protocol, because there is no behavioral variation, only data variation.

```python
@dataclass(frozen=True)
class ProjectType:
    name: str
    artifact_ext: str        # '.zip' or '.jar'
    required_keys: list[str] # config keys validated by checks.py before push
    artifact_strategy: str   # 'build_zip' | 'build_jar' | 'explicit'

PROJECT_TYPES: dict[str, ProjectType] = {
    'resourcepack': ProjectType('resourcepack', '.zip', [],          'build_zip'),
    'world':        ProjectType('world',        '.zip', [],          'explicit'),
    'mod':          ProjectType('mod',          '.jar', ['loaders'], 'build_jar'),
    'shader':       ProjectType('shader',       '.zip', [],          'build_zip'),
    'datapack':     ProjectType('datapack',     '.zip', [],          'build_zip'),
}
```

`artifact_strategy` values:

- `'build_zip'`: `ArtifactFinder` locates `{slug}-{version}.zip` in the project directory (build output).
- `'build_jar'`: `ArtifactFinder` locates `{slug}-{version}.jar` in `build/libs/` (Gradle output).
- `'explicit'`: No build step — user must set `artifact:` path in `puppy.yaml`. Preflight raises an error if absent.

World saves use `'explicit'` because they are exported manually from Minecraft (File → Export World), not produced by a build system. There is no predictable output path to discover.

Sites keep their own type maps for site-specific IDs (`_CLASS_IDS`, `_PROJECT_TYPES`).
`PROJECT_TYPES` is the authority for everything else.

**Adding a new type:** one entry in `PROJECT_TYPES`, plus an entry in each site's type map (or leave it absent so `supports()` returns False).
No pipeline code changes.

---

## `PushContext`

Passed to every `Site` push method.
Pre-computed before iterating over sites.

```python
@dataclass
class PushContext:
    project: Project          # name, slug, root path
    config: dict              # full merged config for this site
    site_config: dict         # config[site.name] section only
    project_type: str         # 'resourcepack' | 'world' | 'mod'
    auth: dict                # full auth.yaml contents
    description: str          # rendered and format-converted for this site
    icon: ProcessedImage      # resized/encoded icon
    gallery: list[ProcessedImage]  # resized/encoded gallery images
    banner: ProcessedImage | None
    logo: ProcessedImage | None
    version: str | None
    artifact: Path | None     # ZIP or JAR path (None unless -p)
    force: bool
    dry_run: bool
    verbosity: int
```

`PushContext` is built once per project, then cloned per site (with `description` and `site_config` substituted).
Sites read from context; they do not mutate it.

---

## `PulledData`

Returned by `Site.pull()`.

```python
@dataclass
class PulledData:
    description: str          # raw description in site's native format
    icon_url: str | None
    gallery_urls: list[str]
    metadata: dict            # title, summary, links, categories, license — site-specific keys
```

`puller.py` converts each field to local files.

---

## Project Type Handling

Each site declares its type map internally.
Example pattern:

```python
class CurseForgeSite(Site):
    _CLASS_IDS = {
        'resourcepack': 12,
        'world': 17,
        'mod': 6,
    }

    def supports(self, project_type: str) -> bool:
        return project_type in self._CLASS_IDS

    def _class_id(self, project_type: str) -> int:
        return self._CLASS_IDS[project_type]
```

```python
class ModrinthSite(Site):
    _PROJECT_TYPES = {
        'resourcepack': 'resourcepack',
        'mod': 'mod',
        # 'world' absent → supports() returns False
    }

    def supports(self, project_type: str) -> bool:
        return project_type in self._PROJECT_TYPES
```

**Adding a new project type** (e.g., `datapack`):
1. Add `'datapack'` to the schema type enum.
2. In each site class: add `'datapack'` to the type map, or leave it absent so `supports()` returns False.
3. The pipeline (`syncer.py`, `publisher.py`) does not change.

**File extension** is resolved from type, not hardcoded per-operation:

```python
ARTIFACT_EXTENSION = {
    'resourcepack': '.zip',
    'world': '.zip',
    'mod': '.jar',
}
```

---

## `AuthFlow` Protocol

Each site provides an `AuthFlow` that the `auth` command delegates to.

```python
class AuthFlow:
    site_name: str
    login_url: str

    def extract_automated(self, page) -> dict:
        """Given a logged-in Playwright page, extract credentials.
        Returns a dict of credential keys (matches auth.yaml structure).
        Raises AutomatedExtractionFailed if selectors not found."""

    def fallback_instructions(self) -> str:
        """Instructions shown in the overlay when automated extraction fails."""

    def auth_yaml_keys(self) -> list[str]:
        """Which keys this flow produces, for overlay input prompts."""
```

`puppy auth` iterates active sites, calls `site.auth_flow()`, runs the flow, writes results to `auth.yaml`.
Adding a new site with a new auth mechanism means implementing `AuthFlow` inside that site class — the `auth` command does not change.

---

## Push Pipeline (`syncer.py`)

```
load config
render descriptions (Jinja2 → site format)
process images (Pillow)
build PushContext

for each active site:
    if not site.supports(project_type): skip silently
    site.validate_auth(auth)          → AuthExpiredError if bad
    site.push_icon(ctx)
    site.push_gallery(ctx)
    site.push_metadata(ctx)
    if pack flag:
        if site.needs_upload(ctx) or force:
            site.push_file(ctx)

print after_push reminders
```

Each step is a discrete call.
A site can no-op any step (e.g., PMC may not support icon upload via API; it handles it inside `push_icon`).

---

## `puppy.yaml` — Full Schema

```yaml
# Identity
name: Neon Glow          # display name; derived from directory name if absent
pack: neonglow           # slug; derived by lowercasing name if absent
type: resourcepack       # resourcepack (default) | world | mod
version: "1.2.0"         # overridable with -V

# Assets (paths relative to project root)
icon: pack.png
banner: banner.png       # optional
logo: logo.png           # optional

# Mod-only fields
loaders:
  - fabric
  - neoforge
java: 21
dependencies:
  fabric-api: required   # required | optional | incompatible

# Post-push reminders
after_push: "Update the forum thread."

# Cross-project URL references (for use in description templates)
# type is required: sites use it to construct the correct URL path.
# Sibling projects (same puppy home) are resolved automatically from their
# own puppy.yaml — no related: entry needed for them.
related:
  fabric-api:
    type: mod
    modrinth: P7dR8mSH
    curseforge: 306612
  my-shader:
    type: shader
    curseforge: 99999

# Per-site overrides
curseforge:
  id: 12345
  slug: neon-glow
  category: Realistic

modrinth:
  id: abcd1234
  slug: neon-glow

planetminecraft:
  slug: neon-glow
  category: Realistic
  after_push: "Update PMC download link."
```

---

## `auth.yaml`

```yaml
curseforge:
  cookie: <session cookie>   # used for _api/ (metadata, gallery, icon)
  token: <API token>         # used for official file upload API
modrinth:
  token: <PAT>
planetminecraft:
  cookie: <session cookie>
```

Never committed to version control.

---

## Image Processing (`imaging.py`)

All resizing uses `Image.LANCZOS`.
Images meeting size/format requirements are passed through without re-encoding.

| Asset | Target | Fit | Format | Quality |
|-------|--------|-----|--------|---------|
| Icon | 512×512 | exact (must be square) | PNG | — |
| Gallery | 1920×1080 max | fit inside, no crop | JPEG | 95% |
| Banner | 1920×1080 max | fit inside, no crop | JPEG | 95% |
| Logo | 1280×256 max | fit inside, no crop | PNG | — |

`imaging.py` returns `ProcessedImage(data: bytes, format: str, width: int, height: int)`.
Non-square icon raises `ValueError` before any API calls.

---

## Commands

### `puppy push`
```
puppy push [project ...] [-s SITE] [-V VERSION] [-p] [-f] [-n] [-q|-vv] [-d PATH]
```
Runs the push pipeline above.

### `puppy pull`
```
puppy pull [project ...] [-s SITE] [-I] [-d PATH]
```
Downloads description, icon, and (with `-I`) gallery from sites into local files.

### `puppy create`
```
puppy create [project ...] [-s SITE] [-f] [-d PATH]
```
Creates new projects on sites; writes returned IDs to `puppy.yaml`.
Prompts for confirmation unless `-f`.

### `puppy init`
```
puppy init [-d PATH]
```
Scaffolds a minimal `puppy.yaml` in the project directory.

### `puppy auth`
```
puppy auth [--site SITE]
```
Opens headed Chromium (requires `puppy[pmc]`).
Per-site flow:
1. Navigate to login page with overlay: "Log in — credentials will be extracted automatically."
2. Poll for successful login.
3. Call `site.auth_flow().extract_automated(page)`.
4. On `AutomatedExtractionFailed`: show overlay with fallback instructions and input field.
5. Write credentials to `auth.yaml`.

Re-run per site to refresh expired cookies: `puppy auth --site curseforge`.

### `puppy clean`
```
puppy clean [-d PATH]
```
Removes `debug/` and other generated artifacts.

---

## Auth Error Handling

`AuthExpiredError` is raised by site classes on HTTP 401/403 or login redirect.
`syncer.py` catches it, prints the message without traceback, exits non-zero.

```
Error: CurseForge session expired — run: puppy auth --site curseforge
```

| Site | Signal | Detection |
|------|--------|-----------|
| Modrinth | HTTP 401 | status code |
| CF official API | HTTP 401/403 | status code |
| CF `_api/` | HTTP 403 | status code |
| PMC | redirect to login | redirect URL |

Other HTTP errors print status code + response body and exit non-zero.

---

## Preflight Checks (`checks.py`)

Runs before any API calls:

- `auth.yaml` exists and has keys for active sites
- Icon file exists and is square
- `loaders` present when `type: mod`
- `id` present for active sites on push/pull (not required for `create`)
- Warn (not error) if `type: mod` and `java` absent

---

## Multi-project Mode

Top-level `puppy.yaml` lists sub-projects:

```yaml
projects:
  - neonglow
  - shimmer
```

Each sub-project has its own `puppy.yaml`.
`auth.yaml` lives at the top level.
`puppy push` from any directory processes all projects; `puppy push neonglow` limits to one.

---

## Dry Run

`puppy push -n` runs the full pipeline including Jinja2 rendering and image processing.
No API calls.
Writes rendered payloads and processed images to `debug/{site}/`.
Opens HTML preview in browser unless `--no-open`.
