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
Auth: `auth.curseforge.cookie` (same as PU today).
Base URL: `https://authors.curseforge.com/_api/`.

Operations needed:
- Upload icon: `POST /projects/game/432/upload-avatar`
- List gallery images: `GET /projects/{id}/media`
- Delete gallery image: `DELETE /projects/{id}/media/{mediaId}`
- Upload gallery image: `POST /projects/{id}/media`
- Update details (description, socials, donation): `PATCH /projects/{id}` or equivalent

Extend existing `CurseForgeSite` class in `sites.py` with these methods.
CF API is not publicly documented; reverse-engineer from PU's `curseforge.js` and browser DevTools.

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

### 1.4 Planet Minecraft

Effort: **1–2 weeks** (PMC blocks non-browser HTTP).
Optional dependency: `pip install puppy[pmc]` installs `playwright`.
One-time setup: `playwright install chromium`.

New module: `puppy/pmc_browser.py`.
Operations: login via session cookie, navigate to manage page, fill and submit description/image forms.
PMC form fields need reverse-engineering from browser DevTools.

Until this is built, PMC push remains routed through PU (hybrid mode), or is skipped.

### 1.5 Remove PU Dependency

Once 1.2–1.4 are done:
- Delete `puppy/worker.py`
- Remove PU-specific code from `puppy/runner.py`: `WORKER_DIR`, `_worker_prep`, `_write_auth`, `_patch_settings`
- Rewrite `puppy/syncer.py`: remove staging-to-PU-dir logic, call native site methods directly
- Remove Node/npm checks from `puppy/checks.py`
- Remove `run/mods` working directory reference
- Update `README.md`: no longer requires Node, npm, or `~/PackUploader`

### 1.6 Testing

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

### Resource Packs
Currently supported sites (CF, Modrinth, PMC) cover the field.
No significant gaps.

### World Saves
- **CurseForge**: major platform, well-supported (classId 17 — Maps)
- **Planet Minecraft**: major platform for maps/worlds
- **Modrinth**: no world project type; skip
- **Missing**: no other platforms worth adding — niche map sites (mc-maps.com, minecraftWorldMap.com) have minimal traffic and no useful APIs

### Mods
- **CurseForge**: essential — dominant mod platform
- **Modrinth**: essential — fast-growing, modern API, increasingly the primary platform
- **GitHub Releases**: standard for mod authors; already handled by mc-publish for packs, should extend naturally to mods
- **Planet Minecraft**: not relevant for mods; skip
- **Hangar / Spigot / Bukkit**: Paper/Bukkit plugin ecosystem — entirely different from Fabric/Forge, out of scope
- **Missing**: nothing significant beyond CF + Modrinth + GitHub Releases

## Effort Summary

| Phase | Scope | Estimate |
|-------|-------|----------|
| 1.1 Image processing | Pillow resize | 0.5 days |
| 1.2 CF native | REST API calls | 2–3 days |
| 1.3 Modrinth native | REST API calls | 1–2 days |
| 1.4 PMC native | Playwright browser | 1–2 weeks |
| 1.5 Remove PU | Cleanup | 1 day |
| 2 Worlds | CF + PMC branching | 3–5 days |
| 3 Mods | CF + Modrinth + loaders | 1–2 weeks |
| **Total** | | **5–10 weeks** |

PMC dominates the estimate.
CF + Modrinth native (no PMC) could ship in ~1 week, with PMC still going through PU temporarily.
