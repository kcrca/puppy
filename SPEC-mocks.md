# Spec: Site Mocks for Testing

---

## Injection Point

Site classes accept base URL constructor parameters so tests redirect traffic to localhost:

```
CurseForgeSite(api_base=..., dash_base=...)
ModrinthSite(api_base=...)
PlanetMinecraftSite()   # no URL — PMC is injected at the pmc_browser module boundary
```

Production URLs are defaults; no other code changes needed.

---

## HTTP Sites: `MockServer`

A real `http.server.HTTPServer` on a random port in a daemon thread.
Routes are registered as `(method, path_regex) → handler(request) → (status, body)`.
First matching route wins.

Every incoming request is appended to a log.
Tests read the log to assert on headers, multipart bodies, query params.

### `RecordedRequest`

Fields: `method`, `path`, `query: dict`, `headers: dict`, `body: bytes`.

Methods:
- `.json()` — parse body as JSON
- `.multipart()` — parse `multipart/form-data` body using Python's `email` module; returns `{field_name: bytes}`
- `.multipart_files()` — returns `{field_name: (filename, bytes)}` for file parts only

### Server query helpers

- `.requests(method=None, path=None)` — filtered list from log; `path` is a regex
- `.last(method, path)` — last matching request; raises `AssertionError` with full log if none
- `.assert_not_called(method, path)` — inverse assertion
- `.clear()` — reset log between tests

---

## `CurseForgeServer`

Covers both the official upload API (`/api/`) and the internal dashboard API (`/_api/`).
Both go to the same server; tests set `api_base` and `dash_base` to the same URL.

### State (`CFProjectState`)

```
id: str
name: str
description: str          updated by POST /_api/projects/description/{id}
icon_url: str             updated by POST /_api/projects/{id}/upload-avatar
gallery: list[CFGalleryItem]  {id, title, url}  mutated by upload/delete routes
latest_file_display_name: str  updated by POST /api/projects/{id}/upload-file
latest_file_size: int          ditto
```

### Routes (all stateful)

| Method | Path pattern | Behaviour |
|--------|-------------|-----------|
| GET | `/_api/projects/{id}` | returns state |
| POST | `/_api/projects/{id}/update-details` | updates `state.name` |
| POST | `/_api/projects/description/{id}` | updates `state.description` |
| POST | `/_api/projects/{id}/upload-avatar` | updates `state.icon_url`; records filename |
| GET | `/_api/image-attachments/{id}` | returns `state.gallery` |
| POST | `/_api/image-attachments/{id}` | appends item to `state.gallery`; auto-assigns id |
| DELETE | `/_api/image-attachments/{id}/{imageId}/1` | removes item from `state.gallery` |
| POST | `/_api/image-attachments/{id}/update-display-order` | no-op; recorded for assertion |
| POST | `/_api/project-license/{id}/update` | no-op; recorded |
| POST | `/_api/project-source/{id}/update` | no-op; recorded |
| GET | `/_api/project-files` | returns `[{displayName, size}]` if file uploaded, else `[]` |
| POST | `/api/projects/{id}/upload-file` | updates `state.latest_file_*`; returns `{id: 999}` |

Auth failure injection: construct with `fail_on='/_api/'` to return 403 on matching paths.

---

## `ModrinthServer`

### State (`MRProjectState`)

```
id: str
slug: str
title: str
description: str          body field
icon_url: str | None      updated by PATCH /icon
gallery: list[MRGalleryItem]  {url, title, ordering}
versions: list[MRVersion]     {version_number, sha512, loaders}
project_type: str
license_id: str
```

### Routes (all stateful)

| Method | Path pattern | Behaviour |
|--------|-------------|-----------|
| GET | `/v2/project/{id}` | returns state |
| PATCH | `/v2/project/{id}` | updates `description`, `title`, `license_id` |
| PATCH | `/v2/project/{id}/icon` | updates `state.icon_url`; ext from query param |
| GET | `/v2/project/{id}/gallery` | returns `state.gallery` |
| POST | `/v2/project/{id}/gallery` | appends item; title and ordering from query params |
| DELETE | `/v2/project/{id}/gallery` | removes by `url` query param |
| GET | `/v2/project/{id}/version` | returns `state.versions` with SHA-512 hashes |
| POST | `/v2/version` | appends version; computes SHA-512 of file part; records loaders |
| POST | `/v2/project` | create project; returns `{id, slug}` |

Auth failure injection: construct with `fail_auth=True` to return 401 on all requests.

---

## PMC: `MockPage`

Injected at the module boundary:

```python
monkeypatch.setattr('puppy.pmc_browser.get_page', lambda cookie: MockPage())
```

`get_page` returns a context manager; `MockPage` implements `__enter__`/`__exit__`.

### Recorded calls

Every Playwright method call is appended to `page.calls` as `(method, args, kwargs)`.

Methods to implement: `goto`, `fill`, `click`, `set_input_files`, `wait_for_selector`, `query_selector`, `evaluate`, `content`.

### State

`page.url` — updated on each `goto(url)`.
Auth failure mode: `goto()` sets `url` to the PMC login URL instead of the target.
Site code detects the redirect and raises `AuthExpiredError`.

### Test helpers

- `.navigated_to() → list[str]` — all URLs passed to `goto()`
- `.filled() → dict[str, str]` — `{selector: last_value}` for all `fill()` calls
- `.uploaded_files() → dict[str, any]` — `{selector: files}` for `set_input_files()`
- `.was_submitted() → bool` — True if any `click()` targeted a submit/save selector
- `.set_selector_value(selector, text)` — configure what `query_selector()` returns

---

## pytest fixtures

Defined in `conftest.py`:

```
cf_server      CurseForgeServer — started/stopped around each test
mr_server      ModrinthServer   — started/stopped around each test
pmc_page       MockPage()
pmc_page_auth_fail  MockPage(simulate_auth_failure=True)
```

Servers start on a random port; no port conflicts possible.

---

## What each site test suite covers

### CurseForge

- `push_icon` sends PNG bytes to upload-avatar; cookie header present
- `push_gallery` with stale items: DELETE called for each stale; POST called for each new; final `state.gallery` matches desired
- `push_gallery` with no changes: no DELETE or POST calls
- `push_metadata` updates `state.description` and `state.name`
- `push_file` sends correct MIME type (ZIP for packs, JAR for mods); `state.latest_file_display_name` contains version
- `needs_upload` returns False when `state.latest_file_display_name` matches version and size matches
- `needs_upload` returns True when no file uploaded yet
- 403 on any `/_api/` call → `AuthExpiredError` with correct message

### Modrinth

- `supports('world')` returns False
- `push_icon` sets `state.icon_url`; ext matches image type
- `push_gallery` sync: same stale/new/unchanged assertions as CF
- `push_metadata` updates `state.description` and `state.license_id`
- `push_file` for mod: `state.versions[0].loaders` matches config loaders
- `needs_upload` returns False when artifact SHA-512 matches a version in `state.versions`
- 401 → `AuthExpiredError` with correct message

### Planet Minecraft

- `supports('mod')` returns False
- `push_metadata` for `type: world` navigates to `/account/manage/projects/`, not `/texture-packs/`
- `push_metadata` fills description field with BBCode-converted text
- `push_metadata` calls `was_submitted()` True
- `push_file` calls `set_input_files` with the artifact path
- Auth failure → `AuthExpiredError` with correct message
