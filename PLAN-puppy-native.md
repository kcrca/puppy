# Plan: Puppy Native — Drop PackUploader, Add Worlds and Mods

This plan is to explore one approach for supporting other kinds of projects.
In this approach, we would make puppy directly talk to remote sites, bypassing PackUploader.
See "**Plan: Extend PackUploader for Worlds and Mods, Puppy Uses PU**" to explore a different approach.

## Goal

Replace PackUploader entirely with native Python.
Add support for world saves and mods on top of the native layer.

## Phase 1: Native API Layer (replaces PU for resource packs)

### 1.1 Image Processing

PU uses `sharp`; Python has Pillow (already a dependency).
New module: `puppy/imaging.py`.

| Asset | Resize | Format |
|-------|--------|--------|
| Icon | 512×512 | PNG |
| Gallery images | 1920×1080 max, fit inside | JPEG 95% |
| Logo | 1280×256 max, fit inside | PNG |
| Thumbnail | 1920×1080 max, fit inside | JPEG 95% |

Pillow's `Image.LANCZOS` resampling matches sharp's output quality closely enough.

### 1.2 CurseForge Native

Effort: **2–3 days**.

**Two separate CF APIs in use:**

`https://minecraft.curseforge.com/api/` — **official, documented** ([authors.curseforge.com/docs/api](https://authors.curseforge.com/docs/api)).
Covers only file upload (`POST /projects/{id}/upload-file`) and game metadata lookups.
Requires API token via `X-Api-Token` header.

`https://authors.curseforge.com/_api/` — **internal, undocumented**.
Used by CF's own authors dashboard frontend.
No public spec, no stability guarantees, no changelog.
In practice: stable for at least 21 months (PU's curseforge.js history shows no endpoint-repair commits since August 2024).
No other known third-party tools use these endpoints.

Operations split by API:

| Operation | API | Endpoint |
|-----------|-----|----------|
| Upload file | Official | `POST /api/projects/{id}/upload-file` |
| Upload icon | Internal `_api/` | `POST /projects/game/432/upload-avatar` |
| List gallery | Internal `_api/` | `GET /image-attachments/image/{id}` |
| Delete gallery image | Internal `_api/` | `DELETE /image-attachments/{id}/{imageId}/1` |
| Upload gallery image | Internal `_api/` | `POST /image-attachments/{id}` |
| Update details/description | Internal `_api/` | `POST /projects/description/{id}`, `POST /projects/{id}/update-details` |
| Update license | Internal `_api/` | `POST /project-license/{id}/update` |
| Update source/links | Internal `_api/` | `POST /project-source/{id}/update` |

Auth: official API uses API token; internal `_api/` uses session cookie (`auth.curseforge.cookie`).

Extend existing `CurseForgeSite` class in `sites.py` with these methods.
Reverse-engineer internal endpoints from PU's `curseforge.js` (already done) and verify against browser DevTools.

### 1.3 Modrinth Native

Effort: **1–2 days**.
Auth: Modrinth API token (already used for `needs_upload` and `resolve_id`).
API is well-documented at `docs.modrinth.com`.

Operations needed:
- Upload icon: `PATCH /v2/project/{id}/icon`
- List gallery: `GET /v2/project/{id}/gallery`
- Delete gallery image: `DELETE /v2/project/{id}/gallery?url={url}`
- Upload gallery image: `POST /v2/project/{id}/gallery`
- Update details: `PATCH /v2/project/{id}` (description, links, categories, license)

Extend existing `ModrinthSite` class in `sites.py`.

### 1.4 Auth Error Detection

All site classes catch auth-related errors reactively and surface a clear message.

| Site | Auth failure signal | Detection |
|------|--------------------|-----------| 
| Modrinth | HTTP 401 | Check status code |
| CF official API | HTTP 401/403 | Check status code |
| CF `_api/` | HTTP 403 | Check status code |
| PMC | HTTP 302 redirect to login page | Check redirect URL |

On detection, raise a named exception (e.g. `AuthExpiredError`) with a message:
`"CurseForge session expired — run: puppy auth --site curseforge"`

Callers in `syncer.py` catch it and print cleanly without a traceback.

### 1.6 Planet Minecraft

Effort: **1–2 weeks** (PMC blocks non-browser HTTP).
Optional dependency: `pip install puppy[pmc]` installs `playwright`.
One-time setup: `playwright install chromium`.

New module: `puppy/pmc_browser.py`.
Operations: login via session cookie, navigate to manage page, fill and submit description/image forms.
PMC form fields need reverse-engineering from browser DevTools.

Until this is built, PMC push remains routed through PU (hybrid mode), or is skipped.

### 1.7 Interactive Auth (`puppy auth`)

Confirmed Phase 1 — not deferred.

New command: `puppy auth [--site cf|modrinth|pmc]`.
Requires Playwright (same optional dependency as PMC).
Replaces manual cookie-hunting in DevTools.

Flow per site:

1. Open headed Chromium to the site's login page.
2. Inject an overlay instructing the user what's about to happen ("Log in, then we'll set up your token automatically").
3. Poll for successful login (auth cookie present or profile element visible).
4. Attempt automated token/cookie extraction:
   - **Modrinth**: navigate to Settings → API tokens, fill form, submit, scrape the generated token value.
   - **CurseForge**: extract session cookies from `authors.curseforge.com` domain (CF has no public token API).
   - **PMC**: extract session cookies (Playwright is used for all PMC operations anyway).
5. If automated extraction fails (selector not found — site redesigned), overlay updates:
   "Couldn't find the token form — things may have changed.
   Go to Settings → API tokens, create one, and paste it below."
   Overlay shows an input field; user pastes; puppy saves it.
6. Write extracted credentials to `auth.yaml`, close browser.
7. Log which path was taken (automated vs. manual fallback) so breakage is visible.

Cookie expiry: CF and PMC session cookies expire on logout or after a period.
`puppy auth` can be re-run per-site: `puppy auth --site curseforge`.
Detect stale auth on 401/redirect during push and print a reminder to re-run `puppy auth`.

### 1.8 Remove PU Dependency

Once 1.2–1.4 are done:
- Delete `puppy/worker.py`
- Remove PU-specific code from `puppy/runner.py`: `WORKER_DIR`, `_worker_prep`, `_write_auth`, `_patch_settings`
- Rewrite `puppy/syncer.py`: remove staging-to-PU-dir logic, call native site methods directly
- Remove Node/npm checks from `puppy/checks.py`
- Remove `run/mods` working directory reference
- Update `README.md`: no longer requires Node, npm, or `~/PackUploader`

### 1.9 Testing

- Unit tests: mock Pillow calls, assert resize parameters
- Integration tests: dedicated test accounts on CF and Modrinth; push known content, read back, assert fields match
- PMC: manual verification only until Playwright path is stable

---

## Phase 2: World Save Support

Prerequisite: Phase 1 complete.
Effort: **3–5 days**.

### Config

New field in `puppy.yaml`:

```yaml
type: world   # or: resourcepack (default), mod
```

### CurseForge

- `classId`: `17` (Worlds/Maps) instead of `12` (Resource Packs)
- Categories: separate world category map (Adventure, Survival, Creative, etc.)
- Output URL: `/minecraft/worlds/{slug}` instead of `/minecraft/texture-packs/{slug}`

### Modrinth

Not applicable — Modrinth has no world project type.
Skip Modrinth silently when `type: world`.

### Planet Minecraft

- Manage URL: `/account/manage/projects/` instead of `/account/manage/texture-packs/`
- Form fields differ from packs; need reverse-engineering against a real world project
- Output URL: `/project/{slug}` instead of `/texture-pack/{slug}`

### Puppy Config Schema

New `puppy.yaml` fields for worlds:

```yaml
type: world
curseforge:
  category: Adventure
planetminecraft:
  category: Survival
```

---

## Phase 3: Mod Support

Prerequisite: Phase 1 complete.
Effort: **1–2 weeks**.

### Config

```yaml
type: mod
loaders:
  - fabric
  - neoforge
java: 21
dependencies:
  fabric-api: required
```

### CurseForge

- `classId`: `6` (Mods)
- Categories: mod-specific category map
- Version upload: include loader and game-version metadata in upload payload
- File: JAR, not ZIP

### Modrinth

- `project_type: "mod"` on project creation
- Version upload: add `loaders` array (fabric, neoforge, forge, quilt) and `dependencies` array with version IDs
- File: JAR
- Modrinth's mod version API is well-documented; this is the most tractable part of Phase 3

### Planet Minecraft

Skip — PMC is not a meaningful platform for mods.

### File Upload (`publisher.py`)

- Detect file type from `type` field: ZIP for packs/worlds, JAR for mods
- Add loader metadata to CF and Modrinth version creation payloads
- Resolve dependency version IDs from Modrinth API before upload

---

## Platform Coverage by Project Type

### Support Matrix

| Type | CurseForge | Modrinth | Planet Minecraft | Notes |
|------|-----------|----------|-----------------|-------|
| **Resource Pack** | ✓ classId 12 | ✓ `resourcepack` | ✓ texture-packs | **Current** |
| **World/Map** | ✓ classId 17 | ✗ no type | ✓ projects/ | **Phase 2** |
| **Mod** | ✓ classId 6 | ✓ `mod` | ~ not meaningful | **Phase 3** |
| **Shader** | ✓ `class=shaders` | ✓ `shader` | ~ customization | High value — same workflow as resource packs |
| **Data Pack** | ~ unclear classId | ✓ `datapack` | ✓ data-packs/ | Near-zero effort after Phase 1 — same ZIP workflow, only classId/project_type differs |
| **Modpack** | ✓ classId 4471 | ✓ `modpack` | ✗ | Low priority — special file formats (.mrpack, manifest), complex dependency manifests |
| **Plugin (Bukkit/Paper)** | ✓ bukkit-plugins | ✓ `plugin` | ✗ | Different ecosystem; Hangar/Spigot are primary; out of scope |
| **Skin** | ~ limited | ✗ no type | ✓ skins/ | No versioning concept; very different workflow; low priority |
| **Server** | ✗ | ✓ `minecraft_java_server` | ✗ | Not a publishing use case |

Legend: ✓ = supported with classId/type, ~ = partial or uncertain, ✗ = not supported

CF classIds confirmed: resource packs (12), worlds (17), mods (6), modpacks (4471), shaders (dedicated class), bukkit plugins (dedicated class).
Modrinth types confirmed via API (`/v2/tag/project_type`): mod, modpack, resourcepack, shader, plugin, datapack, minecraft_java_server.
PMC types from site navigation; no API — all Playwright-driven.

### Future Type Priority

**Shaders** are the most natural next type after mods.
The workflow is nearly identical to resource packs (ZIP file, icon, gallery, description) with the same three sites.
Only difference: different classId on CF and `project_type: "shader"` on Modrinth.
Estimated effort: 0.5 days once Phase 1 is complete.

**Data Packs** are server-side logic (recipes, loot tables, advancements, world gen); resource packs are client-side assets.
Both are ZIPs with `pack.mcmeta`; different internal structure (`data/` vs `assets/`) but identical from a publishing perspective.
"Texture pack" is just the legacy name for resource pack — not a separate type.
Adding `type: datapack` is nearly zero work: swap classId on CF and `project_type` on Modrinth; file handling, image pipeline, and description rendering are unchanged.
Modrinth and PMC both have dedicated sections; CF classId needs verification against CF categories API.
Estimated effort: 0.5 days.

**Modpacks** require special file formats (`.mrpack` for Modrinth, `manifest.json` + overrides ZIP for CF) and dependency resolution.
Substantially more complex than other types; separate project when/if needed.

**Plugins** are a different ecosystem (Bukkit/Paper/Spigot).
Hangar and Spigot are the primary platforms, not CF/Modrinth/PMC.
Out of scope.

**Skins** have no versioning concept and a fundamentally different workflow.
Not a fit for puppy's version-centric model.

### Resource Packs
Currently supported sites (CF, Modrinth, PMC) cover the field.
No significant gaps.

### World Saves
- **CurseForge**: major platform, well-supported (classId 17 — Maps)
- **Planet Minecraft**: major platform for maps/worlds
- **Modrinth**: no world project type; skip
- **Missing**: no other platforms worth adding — niche map sites (mc-maps.com, minecraftWorldMap.com) have minimal traffic and no useful APIs.
  9Minecraft aggregates/mirrors content without an upload API.
  Checked May 2026; no new major platforms found.

### Mods
- **CurseForge**: essential — dominant mod platform
- **Modrinth**: essential — fast-growing, modern API, increasingly the primary platform
- **GitHub Releases**: standard for mod authors; out of scope for puppy.
  GitHub Releases requires a git tag and is distribution infrastructure, not discovery.
  Mod authors should use mc-publish in CI (same as Philter's publish workflow).
- **Planet Minecraft**: not relevant for mods; skip
- **Hangar / Spigot / Bukkit**: Paper/Bukkit plugin ecosystem — entirely different from Fabric/Forge, out of scope
- **FTB / Technic**: modpack launchers, not mod hosting platforms — authors don't publish individual mods there
- **Missing**: nothing significant beyond CF + Modrinth + GitHub Releases.
  Checked May 2026; no new major platforms found.

## Effort Summary

| Phase | Scope | Estimate |
|-------|-------|----------|
| 1.1 Image processing | Pillow resize | 0.5 days |
| 1.2 CF native | REST API calls | 2–3 days |
| 1.3 Modrinth native | REST API calls | 1–2 days |
| 1.4 Auth error detection | Reactive 401/redirect handling | 0.5 days |
| 1.6 PMC native | Playwright browser | 1–2 weeks |
| 1.7 Interactive auth | `puppy auth` Playwright flow | 1–2 days |
| 1.8 Remove PU | Cleanup | 1 day |
| 2 Worlds | CF + PMC branching | 3–5 days |
| 3 Mods | CF + Modrinth + loaders | 1–2 weeks |
| **Total** | | **5–10 weeks** |

PMC dominates the estimate.
CF + Modrinth native (no PMC) could ship in ~1 week, with PMC still going through PU temporarily.
