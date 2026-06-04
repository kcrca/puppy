"""
Sketch: native site implementations.

This replaces sites.py once PU is removed.
Kept separate during transition so both can coexist.

HTTP helper convention:
  _get(url, headers)             → parsed JSON
  _post_json(url, headers, body) → parsed JSON
  _post_multipart(url, headers, fields, files) → parsed JSON
  _patch_json(url, headers, body) → parsed JSON
  _delete(url, headers)           → None

All helpers raise AuthExpiredError on 401/403 (after checking body for auth signals),
SiteError on other 4xx/5xx.
"""
from __future__ import annotations

import email.mime.multipart
import hashlib
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from puppy.errors import AuthExpiredError, SiteError
from puppy.renderer import md_to_bbcode, md_to_html


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class ProcessedImage:
    data: bytes
    filename: str
    mime_type: str   # 'image/png' or 'image/jpeg'


@dataclass
class PushContext:
    project_id: str          # site-specific project ID
    project_slug: str
    project_type: str        # 'resourcepack' | 'world' | 'mod'
    auth: dict
    description: str         # already rendered + format-converted for this site
    icon: ProcessedImage
    gallery: list[ProcessedImage]
    banner: ProcessedImage | None
    logo: ProcessedImage | None
    version: str | None
    artifact: Path | None    # ZIP or JAR; None unless -p
    site_config: dict        # config[site.name] section
    force: bool = False
    dry_run: bool = False
    verbosity: int = 1


@dataclass
class PulledData:
    description: str
    icon_url: str | None
    gallery_urls: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get(url: str, headers: dict) -> Any:
    req = urllib.request.Request(url, headers=headers)
    return _send(req)


def _post_json(url: str, headers: dict, body: dict) -> Any:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={**headers, 'Content-Type': 'application/json'}, method='POST')
    return _send(req)


def _patch_json(url: str, headers: dict, body: dict) -> Any:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={**headers, 'Content-Type': 'application/json'}, method='PATCH')
    return _send(req)


def _delete(url: str, headers: dict) -> None:
    req = urllib.request.Request(url, headers=headers, method='DELETE')
    _send(req)


def _post_multipart(url: str, headers: dict, fields: dict, files: list[tuple[str, str, bytes, str]]) -> Any:
    # files: list of (field_name, filename, data, mime_type)
    boundary = b'----PuppyBoundary'
    body_parts = []
    for name, value in fields.items():
        body_parts.append(
            f'--{boundary.decode()}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    for field_name, filename, data, mime_type in files:
        body_parts.append(
            f'--{boundary.decode()}\r\nContent-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\nContent-Type: {mime_type}\r\n\r\n'.encode()
            + data + b'\r\n'
        )
    body_parts.append(f'--{boundary.decode()}--\r\n'.encode())
    body = b''.join(body_parts)
    req = urllib.request.Request(url, data=body, headers={
        **headers,
        'Content-Type': f'multipart/form-data; boundary={boundary.decode()}',
    }, method='POST')
    return _send(req)


def _send(req: urllib.request.Request) -> Any:
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            if body:
                return json.loads(body)
            return None
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        if e.code in (401, 403):
            raise AuthExpiredError(e.code, body)
        raise SiteError(e.code, body)


# ── Base Site ─────────────────────────────────────────────────────────────────

class Site:
    name: str
    aliases: list[str]
    label: str

    _CLASS_IDS: dict[str, int] = {}     # override in subclasses
    _PROJECT_TYPES: dict[str, str] = {} # override in subclasses that use string types

    def supports(self, project_type: str) -> bool:
        return True

    def push_icon(self, ctx: PushContext) -> None: pass
    def push_gallery(self, ctx: PushContext) -> None: pass
    def push_metadata(self, ctx: PushContext) -> None: pass
    def push_file(self, ctx: PushContext) -> None: pass
    def needs_upload(self, ctx: PushContext) -> bool: return True
    def pull(self, ctx: PushContext) -> PulledData: raise NotImplementedError
    def create(self, ctx: PushContext) -> str: raise NotImplementedError
    def validate_auth(self, auth: dict) -> None: pass
    def convert_description(self, text: str, source_format: str) -> str: return text
    def url_for(self, site_config: dict) -> str | None: return None
    def puppy_yaml_entry(self, pack: str) -> str: return f'{self.name}:\n  id: null\n  slug: {pack}\n'
    def auth_yaml_entry(self) -> str: return ''
    def preview_rows(self, site_config: dict) -> list[tuple[str, str]]: return []


# ── CurseForge ────────────────────────────────────────────────────────────────

class CurseForgeSite(Site):
    name = 'curseforge'
    aliases = ['cf']
    label = 'CurseForge'

    _API = 'https://minecraft.curseforge.com/api'
    _DASH = 'https://authors.curseforge.com/_api'

    _CLASS_IDS = {
        'resourcepack': 12,
        'world': 17,
        'mod': 6,
    }

    # CF release types: 1=release, 2=beta, 3=alpha
    _RELEASE_TYPES = {'release': 1, 'beta': 2, 'alpha': 3}

    def supports(self, project_type: str) -> bool:
        return project_type in self._CLASS_IDS

    # ── Auth helpers ──

    def _cookie_h(self, auth: dict) -> dict:
        return {'Cookie': auth.get('curseforge', {}).get('cookie', '')}

    def _token_h(self, auth: dict) -> dict:
        return {'X-Api-Token': auth.get('curseforge', {}).get('token', '')}

    def validate_auth(self, auth: dict) -> None:
        cf = auth.get('curseforge', {})
        if not cf.get('cookie'):
            raise AuthExpiredError(0, 'No CurseForge cookie — run: puppy auth --site curseforge')
        if not cf.get('token'):
            raise AuthExpiredError(0, 'No CurseForge token — run: puppy auth --site curseforge')

    # ── Push ──

    def push_icon(self, ctx: PushContext) -> None:
        # POST multipart to _DASH/projects/{id}/upload-avatar
        # field 'avatar': PNG bytes
        if ctx.dry_run:
            return
        try:
            _post_multipart(
                f'{self._DASH}/projects/{ctx.project_id}/upload-avatar',
                self._cookie_h(ctx.auth),
                fields={},
                files=[('avatar', ctx.icon.filename, ctx.icon.data, ctx.icon.mime_type)],
            )
        except AuthExpiredError:
            raise AuthExpiredError(0, 'CurseForge session expired — run: puppy auth --site curseforge')

    def push_gallery(self, ctx: PushContext) -> None:
        if ctx.dry_run:
            return
        pid = ctx.project_id
        h = self._cookie_h(ctx.auth)

        # GET existing: _DASH/image-attachments/{id}?filter={}&range=[0,24]&sort=["id","DESC"]
        params = urllib.parse.urlencode({
            'filter': '{}',
            'range': '[0,24]',
            'sort': '["id","DESC"]',
        })
        existing = _get(f'{self._DASH}/image-attachments/{pid}?{params}', h)
        # existing: list of {id, title, url, ...}

        desired_filenames = {img.filename for img in ctx.gallery}
        existing_by_filename = {item['title']: item for item in existing}

        # Delete images no longer in desired set
        for title, item in existing_by_filename.items():
            if title not in desired_filenames:
                # DELETE _DASH/image-attachments/{id}/{imageId}/1
                _delete(f'{self._DASH}/image-attachments/{pid}/{item["id"]}/1', h)

        # Upload new images
        for img in ctx.gallery:
            if img.filename not in existing_by_filename:
                # POST multipart: fields={title, description}, files=[image]
                _post_multipart(
                    f'{self._DASH}/image-attachments/{pid}',
                    h,
                    fields={'title': img.filename, 'description': ''},
                    files=[('image', img.filename, img.data, img.mime_type)],
                )

        # Reorder to match desired order
        ordered_ids = []
        existing_after = _get(f'{self._DASH}/image-attachments/{pid}?{params}', h)
        by_title = {item['title']: item['id'] for item in existing_after}
        for img in ctx.gallery:
            if img.filename in by_title:
                ordered_ids.append(by_title[img.filename])
        if ordered_ids:
            _post_json(f'{self._DASH}/image-attachments/{pid}/update-display-order', h, ordered_ids)

    def push_metadata(self, ctx: PushContext) -> None:
        if ctx.dry_run:
            return
        pid = ctx.project_id
        h = self._cookie_h(ctx.auth)
        sc = ctx.site_config

        # Description: POST _DASH/projects/description/{id}
        # Body: {description: <html string>}
        _post_json(f'{self._DASH}/projects/description/{pid}', h, {'description': ctx.description})

        # Project details: POST _DASH/projects/{id}/update-details
        # Body: {name, summary, tags (classId + category IDs), socials, donation}
        class_id = self._CLASS_IDS[ctx.project_type]
        details = {
            'classId': class_id,
            'name': sc.get('name', ''),
            'summary': sc.get('summary', ''),
            # categories: list of CF category IDs derived from sc.get('category')
            # socials: {website, github, twitter, ...}
            # donation: {type, value}
        }
        _post_json(f'{self._DASH}/projects/{pid}/update-details', h, details)

        # License: POST _DASH/project-license/{id}/update
        if sc.get('license'):
            _post_json(f'{self._DASH}/project-license/{pid}/update', h, {'license': sc['license']})

        # Source/links: POST _DASH/project-source/{id}/update
        links = sc.get('links') or {}
        if links:
            _post_json(f'{self._DASH}/project-source/{pid}/update', h, {'sourceUrl': links.get('source'), 'wikiUrl': links.get('wiki')})

    def push_file(self, ctx: PushContext) -> None:
        if ctx.dry_run or not ctx.artifact:
            return
        # POST multipart to official API: _API/projects/{id}/upload-file
        # fields: metadata JSON (changelog, changelogType, gameVersions, releaseType, displayName, relations)
        # files: [('file', filename, bytes, 'application/zip' or 'application/java-archive')]
        metadata = {
            'changelog': '',        # from config
            'changelogType': 'markdown',
            'displayName': f'{ctx.project_slug} v{ctx.version}',
            'gameVersions': [],     # resolved from config.versions via CF game versions API
            'releaseType': 'release',
        }
        if ctx.project_type == 'mod':
            # Add loader game version IDs
            # CF represents loaders (Fabric, Forge, NeoForge) as game version entries
            metadata['relations'] = []  # dependency relations
        mime = 'application/java-archive' if ctx.project_type == 'mod' else 'application/zip'
        artifact_bytes = ctx.artifact.read_bytes()
        try:
            _post_multipart(
                f'{self._API}/projects/{ctx.project_id}/upload-file',
                self._token_h(ctx.auth),
                fields={'metadata': json.dumps(metadata)},
                files=[('file', ctx.artifact.name, artifact_bytes, mime)],
            )
        except AuthExpiredError:
            raise AuthExpiredError(0, 'CurseForge token invalid — run: puppy auth --site curseforge')

    def needs_upload(self, ctx: PushContext) -> bool:
        if not ctx.artifact:
            return False
        local_size = ctx.artifact.stat().st_size
        params = urllib.parse.urlencode({
            'filter': json.dumps({'projectId': ctx.project_id}),
            'range': '[0, 0]',
            'sort': '["DateCreated", "DESC"]',
        })
        try:
            files = _get(f'{self._DASH}/project-files?{params}', self._cookie_h(ctx.auth))
        except (AuthExpiredError, SiteError):
            return True   # assume upload needed if check fails
        if not files:
            return True
        latest = files[0]
        return not (
            latest.get('size') == local_size
            and f'v{ctx.version}' in latest.get('displayName', '')
        )

    def pull(self, ctx: PushContext) -> PulledData:
        pid = ctx.project_id
        h = self._cookie_h(ctx.auth)
        project = _get(f'{self._DASH}/projects/{pid}', h)
        description_data = _get(f'{self._DASH}/projects/description/{pid}', h)
        params = urllib.parse.urlencode({'filter': '{}', 'range': '[0,24]', 'sort': '["id","ASC"]'})
        gallery = _get(f'{self._DASH}/image-attachments/{pid}?{params}', h)
        return PulledData(
            description=description_data.get('description', ''),
            icon_url=project.get('avatarUrl'),
            gallery_urls=[item['url'] for item in gallery],
            metadata=project,
        )

    def convert_description(self, text: str, source_format: str) -> str:
        if source_format == 'md':
            return md_to_html(text)
        return text

    def url_for(self, site_config: dict) -> str | None:
        ref = site_config.get('slug') or site_config.get('id')
        if not ref:
            return None
        path = {
            'resourcepack': 'texture-packs',
            'world': 'worlds',
            'mod': 'mc-mods',
        }.get(site_config.get('type', 'resourcepack'), 'texture-packs')
        return f'https://www.curseforge.com/minecraft/{path}/{ref}'

    def auth_yaml_entry(self) -> str:
        return (
            'curseforge:\n'
            '  token: YOUR_CURSEFORGE_API_TOKEN\n'
            '  cookie: CobaltSession=YOUR_COBALT_SESSION_COOKIE\n'
        )


# ── Modrinth ──────────────────────────────────────────────────────────────────

class ModrinthSite(Site):
    name = 'modrinth'
    aliases = ['mr']
    label = 'Modrinth'

    _API = 'https://api.modrinth.com/v2'

    _PROJECT_TYPES = {
        'resourcepack': 'resourcepack',
        'mod': 'mod',
        # 'world' absent — supports() returns False
    }

    _LOADERS = {
        'resourcepack': ['minecraft'],
        'mod': [],   # from config: fabric, neoforge, forge, quilt
    }

    def supports(self, project_type: str) -> bool:
        return project_type in self._PROJECT_TYPES

    # ── Auth helpers ──

    def _headers(self, auth: dict) -> dict:
        token = auth.get('modrinth', {}).get('token') or auth.get('modrinth', '')
        return {
            'Authorization': token,
            'User-Agent': 'puppy/1.0',
        }

    def validate_auth(self, auth: dict) -> None:
        token = auth.get('modrinth', {}).get('token') or auth.get('modrinth', '')
        if not token:
            raise AuthExpiredError(0, 'No Modrinth token — run: puppy auth --site modrinth')

    # ── Push ──

    def push_icon(self, ctx: PushContext) -> None:
        if ctx.dry_run:
            return
        # PATCH /project/{id}/icon?ext=png
        ext = 'png' if ctx.icon.mime_type == 'image/png' else 'jpg'
        req = urllib.request.Request(
            f'{self._API}/project/{ctx.project_id}/icon?ext={ext}',
            data=ctx.icon.data,
            headers={**self._headers(ctx.auth), 'Content-Type': ctx.icon.mime_type},
            method='PATCH',
        )
        _send(req)

    def push_gallery(self, ctx: PushContext) -> None:
        if ctx.dry_run:
            return
        pid = ctx.project_id
        h = self._headers(ctx.auth)

        # GET /project/{id}/gallery → list of {url, title, description, ordering}
        existing = _get(f'{self._API}/project/{pid}/gallery', h)
        existing_by_title = {item['title']: item for item in existing}
        desired_titles = {img.filename for img in ctx.gallery}

        # DELETE stale
        for title, item in existing_by_title.items():
            if title not in desired_titles:
                # DELETE /project/{id}/gallery?url={encoded_url}
                encoded = urllib.parse.quote(item['url'], safe='')
                _delete(f'{self._API}/project/{pid}/gallery?url={encoded}', h)

        # POST new
        for i, img in enumerate(ctx.gallery):
            if img.filename not in existing_by_title:
                # POST /project/{id}/gallery
                # query params: ext, featured, title, description, ordering
                params = urllib.parse.urlencode({
                    'ext': 'png' if img.mime_type == 'image/png' else 'jpg',
                    'featured': 'false',
                    'title': img.filename,
                    'description': '',
                    'ordering': i,
                })
                req = urllib.request.Request(
                    f'{self._API}/project/{pid}/gallery?{params}',
                    data=img.data,
                    headers={**h, 'Content-Type': img.mime_type},
                    method='POST',
                )
                _send(req)

    def push_metadata(self, ctx: PushContext) -> None:
        if ctx.dry_run:
            return
        sc = ctx.site_config
        project_type = self._PROJECT_TYPES[ctx.project_type]
        body = {
            'description': ctx.description,
            'project_type': project_type,
            # categories: list of Modrinth category strings
            # license_id: SPDX string
            # issues_url, source_url, wiki_url, discord_url: from config links
            # donation_urls: list of {id, platform, url}
        }
        if sc.get('license'):
            body['license_id'] = sc['license']
        links = sc.get('links') or {}
        if isinstance(links, dict):
            body.update({k: v for k, v in {
                'issues_url': links.get('issues'),
                'source_url': links.get('source'),
                'wiki_url': links.get('wiki'),
                'discord_url': links.get('discord'),
            }.items() if v})
        _patch_json(f'{self._API}/project/{ctx.project_id}', self._headers(ctx.auth), body)

    def push_file(self, ctx: PushContext) -> None:
        if ctx.dry_run or not ctx.artifact:
            return
        # POST /version (multipart)
        # Part 'data': JSON metadata
        # Part 'file': artifact bytes
        loaders = ctx.site_config.get('loaders') if ctx.project_type == 'mod' else self._LOADERS.get(ctx.project_type, ['minecraft'])
        dependencies = []
        if ctx.project_type == 'mod':
            # Resolve dependency slugs → Modrinth project IDs via GET /project/{slug}
            for dep_name, dep_type in (ctx.site_config.get('dependencies') or {}).items():
                dep_project = _get(f'{self._API}/project/{dep_name}', self._headers(ctx.auth))
                dependencies.append({'project_id': dep_project['id'], 'dependency_type': dep_type})

        metadata = {
            'name': f'{ctx.project_slug} v{ctx.version}',
            'version_number': ctx.version,
            'changelog': '',    # from config
            'dependencies': dependencies,
            'game_versions': [], # resolved from config.versions via Modrinth tags API
            'version_type': 'release',
            'loaders': loaders,
            'featured': True,
            'project_id': ctx.project_id,
            'file_parts': [ctx.artifact.name],
        }
        artifact_bytes = ctx.artifact.read_bytes()
        _post_multipart(
            f'{self._API}/version',
            self._headers(ctx.auth),
            fields={'data': json.dumps(metadata)},
            files=[('file', ctx.artifact.name, artifact_bytes,
                    'application/java-archive' if ctx.project_type == 'mod' else 'application/zip')],
        )

    def needs_upload(self, ctx: PushContext) -> bool:
        if not ctx.artifact:
            return False
        local_hash = hashlib.sha512(ctx.artifact.read_bytes()).hexdigest()
        try:
            versions = _get(
                f'{self._API}/project/{ctx.project_id}/version',
                self._headers(ctx.auth),
            )
        except (AuthExpiredError, SiteError):
            return True
        for v in versions:
            for f in v.get('files', []):
                if f.get('hashes', {}).get('sha512') == local_hash:
                    return False
        return True

    def pull(self, ctx: PushContext) -> PulledData:
        h = self._headers(ctx.auth)
        project = _get(f'{self._API}/project/{ctx.project_id}', h)
        gallery = _get(f'{self._API}/project/{ctx.project_id}/gallery', h)
        return PulledData(
            description=project.get('body', ''),
            icon_url=project.get('icon_url'),
            gallery_urls=[item['url'] for item in gallery],
            metadata=project,
        )

    def create(self, ctx: PushContext) -> str:
        # POST /project (multipart: 'data' JSON + optional icon file)
        project_type = self._PROJECT_TYPES[ctx.project_type]
        body = {
            'slug': ctx.project_slug,
            'title': ctx.site_config.get('name', ctx.project_slug),
            'description': ctx.site_config.get('summary', ''),
            'categories': [],
            'client_side': 'optional',
            'server_side': 'optional',
            'body': ctx.description,
            'project_type': project_type,
            'license_id': ctx.site_config.get('license', 'LicenseRef-All-Rights-Reserved'),
            'is_draft': True,
        }
        result = _post_multipart(
            f'{self._API}/project',
            self._headers(ctx.auth),
            fields={'data': json.dumps(body)},
            files=[('icon', ctx.icon.filename, ctx.icon.data, ctx.icon.mime_type)],
        )
        return result['id']

    def convert_description(self, text: str, source_format: str) -> str:
        return text   # Modrinth accepts Markdown natively

    def url_for(self, site_config: dict) -> str | None:
        ref = site_config.get('slug') or site_config.get('id')
        if not ref:
            return None
        type_path = {'resourcepack': 'resourcepack', 'mod': 'mod'}.get(
            site_config.get('type', 'resourcepack'), 'resourcepack'
        )
        return f'https://modrinth.com/{type_path}/{ref}'

    def auth_yaml_entry(self) -> str:
        return 'modrinth:\n  token: YOUR_MODRINTH_TOKEN\n'

    def resolve_id(self, config: dict, auth: dict, verbosity: int) -> dict:
        mr = config.get('modrinth', {})
        if mr.get('id') or not mr.get('slug'):
            return config
        slug = mr['slug']
        headers = {'User-Agent': 'puppy/1.0'}
        token = auth.get('modrinth', {}).get('token') or auth.get('modrinth', '')
        if token:
            headers['Authorization'] = token
        data = _get(f'{self._API}/project/{slug}', headers)
        config = dict(config)
        config['modrinth'] = dict(mr, id=data['id'], slug=data['slug'])
        if verbosity >= 1:
            print(f"Resolved Modrinth ID for slug '{slug}': {data['id']}")
        return config


# ── Planet Minecraft ──────────────────────────────────────────────────────────

class PlanetMinecraftSite(Site):
    """
    All operations driven by Playwright (headless).
    Requires: pip install puppy[pmc] && playwright install chromium
    """
    name = 'planetminecraft'
    aliases = ['pmc']
    label = 'Planet Minecraft'

    _BASE = 'https://www.planetminecraft.com'

    _MANAGE_PATHS = {
        'resourcepack': '/account/manage/texture-packs/',
        'world': '/account/manage/projects/',
        # 'mod' absent — supports() returns False
    }

    _OUTPUT_PATHS = {
        'resourcepack': '/texture-pack/',
        'world': '/project/',
    }

    def supports(self, project_type: str) -> bool:
        return project_type in self._MANAGE_PATHS

    # ── Playwright helper ──

    def _page(self, auth: dict):
        try:
            from puppy import pmc_browser
        except ImportError:
            raise SystemExit('Planet Minecraft support requires: pip install puppy[pmc] && playwright install chromium')
        return pmc_browser.get_page(auth.get('planetminecraft', {}).get('cookie', ''))

    def validate_auth(self, auth: dict) -> None:
        if not auth.get('planetminecraft', {}).get('cookie'):
            raise AuthExpiredError(0, 'No PMC cookie — run: puppy auth --site pmc')

    # ── Push ──

    def push_icon(self, ctx: PushContext) -> None:
        # Icon is submitted as part of the edit form; handled inside push_metadata.
        pass

    def push_gallery(self, ctx: PushContext) -> None:
        if ctx.dry_run:
            return
        # Playwright: navigate to gallery management section of edit page.
        # For each existing image not in ctx.gallery: click delete.
        # For each new image in ctx.gallery: upload via file input.
        # PMC gallery form selectors TBD from DevTools capture.
        with self._page(ctx.auth) as page:
            slug = ctx.project_slug
            manage_path = self._MANAGE_PATHS[ctx.project_type]
            page.goto(f'{self._BASE}{manage_path}{slug}/')
            _pmc_sync_gallery(page, ctx.gallery)  # helper to be implemented in pmc_browser.py

    def push_metadata(self, ctx: PushContext) -> None:
        if ctx.dry_run:
            return
        with self._page(ctx.auth) as page:
            slug = ctx.project_slug
            manage_path = self._MANAGE_PATHS[ctx.project_type]
            page.goto(f'{self._BASE}{manage_path}{slug}/')
            # Fill form fields: description (BBCode), title, category, tags, resolution, progress
            # Icon: upload file input if present
            # Submit form
            _pmc_fill_and_submit(page, ctx)  # helper to be implemented in pmc_browser.py

    def push_file(self, ctx: PushContext) -> None:
        if ctx.dry_run or not ctx.artifact:
            return
        with self._page(ctx.auth) as page:
            slug = ctx.project_slug
            manage_path = self._MANAGE_PATHS[ctx.project_type]
            page.goto(f'{self._BASE}{manage_path}{slug}/')
            # Upload ZIP via file input on the file upload section of the edit page
            _pmc_upload_file(page, ctx.artifact)  # helper in pmc_browser.py

    def needs_upload(self, ctx: PushContext) -> bool:
        # PMC has no API to query version; use local state file.
        state_path = Path(ctx.site_config.get('_puppy_dir', '.')) / '.publish_state.yaml'
        if not state_path.exists():
            return True
        state = yaml.safe_load(state_path.read_text()) or {}
        return state.get(self.name, {}).get('version') != str(ctx.version)

    def pull(self, ctx: PushContext) -> PulledData:
        # Playwright: navigate to edit page, extract form values.
        with self._page(ctx.auth) as page:
            slug = ctx.project_slug
            manage_path = self._MANAGE_PATHS[ctx.project_type]
            page.goto(f'{self._BASE}{manage_path}{slug}/')
            return _pmc_extract_metadata(page)  # helper in pmc_browser.py

    def convert_description(self, text: str, source_format: str) -> str:
        if source_format == 'md':
            return md_to_bbcode(text)
        return text

    def url_for(self, site_config: dict) -> str | None:
        ref = site_config.get('slug') or site_config.get('id')
        if not ref:
            return None
        path = self._OUTPUT_PATHS.get(site_config.get('type', 'resourcepack'), '/texture-pack/')
        return f'{self._BASE}{path}{ref}/'

    def auth_yaml_entry(self) -> str:
        return 'planetminecraft:\n  cookie: pmc_autologin=YOUR_PMC_AUTOLOGIN_COOKIE\n'


# ── Stubs for pmc_browser helpers (to be fleshed out in pmc_browser.py) ───────

def _pmc_sync_gallery(page, gallery: list[ProcessedImage]) -> None:
    raise NotImplementedError

def _pmc_fill_and_submit(page, ctx: PushContext) -> None:
    raise NotImplementedError

def _pmc_upload_file(page, artifact: Path) -> None:
    raise NotImplementedError

def _pmc_extract_metadata(page) -> PulledData:
    raise NotImplementedError


# ── Registry ──────────────────────────────────────────────────────────────────

CURSEFORGE = CurseForgeSite()
MODRINTH = ModrinthSite()
PMC = PlanetMinecraftSite()

SITES: list[Site] = [CURSEFORGE, MODRINTH, PMC]
SITE_MAP: dict[str, Site] = {s.name: s for s in SITES}
_ALIASES: dict[str, Site] = {alias: s for s in SITES for alias in s.aliases}
