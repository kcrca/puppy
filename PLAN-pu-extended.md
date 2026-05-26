# Plan: Extend PackUploader for Worlds and Mods, Puppy Uses PU

## Goal

Add world save and mod support to PackUploader.
Update puppy to pass the necessary config fields to PU.
Keep puppy's dependency on PU intact; no native API layer needed.

This approach delivers world and mod support in roughly one week total,
compared to 5–10 weeks for the native puppy approach.

---

## Part 1: World Save Support

### 1.1 PU Changes

**`project.json` — new field**

```json
{ "type": "world" }
```

Default: `"resourcepack"` (backwards compatible; existing projects unchanged).

---

**`curseforge.js`**

- `classId`: parameterize based on type.
  `project.config.type === 'world' ? 17 : 12`
- Categories: add a `worldCategories` map alongside the existing pack `categories` map.
  World CF categories include: Adventure, Survival, Creation, Game Map, Puzzle, etc.
  Requires looking up current CF category IDs for the Worlds class.
- Log URL: `/minecraft/worlds/${slug}` instead of `/minecraft/texture-packs/${slug}`

Changes are small and localised.
Estimated effort: **0.5–1 day**.

---

**`planetminecraft.js`**

PMC separates texture packs (`/account/manage/texture-packs/`) from other projects (`/account/manage/projects/`).
Six URL occurrences need parameterizing.

- Manage URL base: parameterize to `/texture-packs/` or `/projects/` based on type
- `target_type` in the tag endpoint: value for worlds needs confirming via DevTools
- `folder_id[]` categories: world categories differ from pack categories; new map required
- Output URL: `/project/{slug}` instead of `/texture-pack/{slug}`
- `createForm` and `updateDetails` form fields: worlds may have additional fields (dimensions, seed, etc.) — need to capture a real world create/update POST in DevTools to confirm

The form field investigation is the main unknown.
Estimated effort: **1–2 days** for URL/category changes + **0.5–1 day** for form field reverse-engineering.

---

**`modrinth.js`**

No changes. Modrinth has no world project type; worlds are silently skipped.

---

### 1.2 Puppy Changes

**`puppy.yaml` schema** — new optional field:

```yaml
type: world   # resourcepack (default) | world | mod
```

**`puppy/syncer.py`** — pass `type` into `project.json`:

```python
project_json = {'config': cfg, 'type': config.get('type', 'resourcepack'), **platform_ids}
```

**`puppy/sites.py`** — `CurseForgeSite` and `ModrinthSite` may need to skip or adjust
`needs_upload()` URL paths for worlds (CF uses `/minecraft/worlds/` not `/texture-packs/`).

**Documentation** — update `puppy.yaml` reference and examples.

Estimated effort: **0.5 day**.

---

## Part 2: Mod Support

### 2.1 PU Changes

**`project.json` — new fields**

```json
{
  "type": "mod",
  "loaders": ["fabric", "neoforge"],
  "java": 21,
  "dependencies": {
    "fabric-api": "required"
  }
}
```

---

**`curseforge.js`**

- `classId: 6` for mods (vs 12 for packs, 17 for worlds)
- Categories: add mod categories map (Magic, Technology, Adventure, etc.)
- Version upload (`uploadPack`): add loader/game-version metadata to the multipart upload payload.
  CF requires specifying mod loader (Fabric, Forge, NeoForge) and compatible game versions.
  File type changes from ZIP to JAR — update the `Content-Type` and filename.
- Log URL: `/minecraft/mc-mods/{slug}`

Estimated effort: **1.5–2 days**.

---

**`modrinth.js`**

- `project_type: "mod"` on project creation (was `"resourcepack"`)
- Version upload (`uploadPack`): add `loaders` array and `dependencies` array.
  Modrinth dependencies require the dependency's project ID, not just its name.
  Need to resolve dependency IDs from Modrinth API before upload (e.g. fabric-api → `P7dR8mSH`).
- File type: JAR

This is the most complex PU change.
Modrinth's API is well-documented, but dependency ID resolution adds a lookup step.
Estimated effort: **1.5–2 days**.

---

**`planetminecraft.js`**

No changes. PMC is not a meaningful platform for mods; skip silently when `type === 'mod'`.

---

**`scripts/details.js`**

Currently assumes all projects are resource packs for image handling and detail updates.
Add type-based branching:
- Mods: skip image upload for sites that don't support it, or handle mod-specific image categories
- Otherwise image handling is the same

Estimated effort: **0.5 day**.

---

### 2.2 Puppy Changes

**`puppy.yaml` schema** — new fields:

```yaml
type: mod
loaders:
  - fabric
  - neoforge
java: 21
dependencies:
  fabric-api: required   # or: optional, incompatible
```

**`puppy/syncer.py`** — pass new fields into `project.json`:

```python
project_json = {
    'config': cfg,
    'type': config.get('type', 'resourcepack'),
    'loaders': config.get('loaders', []),
    'java': config.get('java'),
    'dependencies': config.get('dependencies', {}),
    **platform_ids,
}
```

**`puppy/publisher.py`** — `upload_pack()` uploads the built artifact:
- For mods, find and upload the JAR from `build/libs/` instead of a ZIP
- Pass loader metadata to CF and Modrinth upload APIs

**`puppy/checks.py`** — add validation:
- `loaders` required when `type: mod`
- warn if no `java` specified for mods

**Documentation** — update schema reference and examples with mod config sample.

Estimated effort: **1 day**.

---

## Effort Summary

| Area | Scope | Estimate |
|------|-------|----------|
| PU: worlds CF | classId + categories | 0.5–1 day |
| PU: worlds PMC | URLs + form fields | 1.5–3 days |
| Puppy: worlds | type field passthrough | 0.5 day |
| PU: mods CF | classId + version metadata + JAR | 1.5–2 days |
| PU: mods Modrinth | project_type + loaders + deps | 1.5–2 days |
| PU: details.js branching | type-aware image/detail handling | 0.5 day |
| Puppy: mods | loaders/deps passthrough + JAR upload | 1 day |
| **Total** | | **~1–2 weeks** |

The PMC form field investigation for worlds is the main risk.
Everything else is incremental change to existing, working code.

---

## Platform Coverage by Project Type

### Resource Packs
Currently supported sites (CF, Modrinth, PMC) cover the field.
No significant gaps.

### World Saves
- **CurseForge**: major platform, well-supported (classId 17 — Maps)
- **Planet Minecraft**: major platform for maps/worlds
- **Modrinth**: no world project type; skip silently
- **Missing**: no other platforms worth adding — niche map sites (mc-maps.com, minecraftWorldMap.com) have minimal traffic and no useful APIs

### Mods
- **CurseForge**: essential — dominant mod platform
- **Modrinth**: essential — fast-growing, modern API, increasingly the primary platform
- **GitHub Releases**: standard for mod authors; PU already handles GitHub releases for packs via mc-publish; should extend to mods naturally
- **Planet Minecraft**: not relevant for mods; skip
- **Hangar / Spigot / Bukkit**: Paper/Bukkit plugin ecosystem — entirely different from Fabric/Forge, out of scope
- **Missing**: nothing significant beyond CF + Modrinth + GitHub Releases

## What This Approach Does Not Deliver

- Removal of the Node/npm/`~/PackUploader` dependency
- A pure-Python tool users can `pip install` without further setup

Those goals require the native puppy approach (see `PLAN-puppy-native.md`).
