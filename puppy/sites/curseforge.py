from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from puppy.errors import AuthExpiredError, SiteError
from puppy.http import urlopen_retrying
from puppy.images import find_image, prepare_gallery_image
from puppy.renderer import md_to_html
from puppy.sites.base import Site


_API = 'https://minecraft.curseforge.com/api'
_DASH = 'https://authors.curseforge.com/_api'
_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

_LICENSE_IDS = {
    'Academic Free License v3.0': 3,
    'All Rights Reserved': 1,
    'Apache License version 2.0': 14,
    'Attribution-NonCommercial-ShareAlike 4.0 International': 22004,
    'BSD License': 5,
    'Creative Commons 4.0': 22002,
    'GNU Affero General Public License version 3 (AGPLv3)': 10,
    'GNU General Public License version 2 (GPLv2)': 6,
    'GNU General Public License version 3 (GPLv3)': 7,
    'GNU Lesser General Public License version 2.1 (LGPLv2.1)': 8,
    'GNU Lesser General Public License version 3 (LGPLv3)': 9,
    'ISC License (ISCL)': 18,
    'MIT License': 4,
    'Mozilla Public License 2.0': 22000,
    'Public Domain': 2,
    'zlib/libpng License': 12,
}

_DONATION_TYPES = {
    'none': -1, 'paypal': 1, 'paypalHosted': 2, 'patreon': 6,
    'github': 7, 'kofi': 8, 'buyMeACoffee': 9,
}

_SOCIAL_TYPES = {
    'mastodon': 1, 'discord': 2, 'website': 3, 'facebook': 4, 'twitter': 5,
    'instagram': 6, 'patreon': 7, 'twitch': 8, 'reddit': 9, 'youtube': 10,
    'tiktok': 11, 'pinterest': 12, 'github': 13, 'bluesky': 14,
}

_CATEGORIES = {
    # Pack subcategories (classId=12)
    '16x': 393, '32x': 394, '64x': 395, '128x': 396, '256x': 397,
    '512x and Higher': 398, 'Data Packs': 5193, 'Font Packs': 5244,
    # World subcategories (classId=17)
    'Adventure': 248, 'Creation': 249, 'Game Map': 250, 'Parkour': 251,
    'Puzzle': 252, 'Survival': 253, 'Modded World': 4464,
    # Mod subcategories (classId=6)
    'Adventure and RPG': 422, 'API and Library': 421,
    'Armor, Tools, and Weapons': 434, 'Automation': 4843,
    'Biomes': 407, 'Bug Fixes': 6821, 'Cosmetic': 424,
    'Dimensions': 410, 'Education': 5299, 'Energy': 417,
    'Energy, Fluid, and Item Transport': 415, 'Farming': 416,
    'Food': 436, 'Genetics': 418, 'Magic': 419,
    'Map and Information': 423, 'Miscellaneous': 425, 'Mobs': 411,
    'Ores and Resources': 408, 'Performance': 6814, 'Player Transport': 414,
    'Processing': 413, 'Redstone': 4558, 'Server Utility': 435,
    'Skyblock': 6145, 'Storage': 420, 'Structures': 409,
    'Technology': 412, 'Utility & QoL': 5191, 'World Gen': 406,
}
_CATEGORIES_LOWER = {k.lower(): v for k, v in _CATEGORIES.items()}

_ENV_CLIENT = 9638
_ENV_SERVER = 9639

_CLASS_IDS = {
    'pack': 12,
    'mod': 6,
    'world': 17,
}

_DEFAULT_CATEGORIES = {
    'pack': 393,   # 16x resolution
    'mod': 425,    # Miscellaneous
    'world': 253,  # Survival
}

_URL_SEGMENTS = {
    'pack': 'texture-packs',
    'mod': 'mc-mods',
    'world': 'worlds',
}

_BEDROCK_CLASS_ID = 4559

_BEDROCK_DEFAULT_CATEGORIES = {
    'pack': 4561,  # Resource Packs under Addons
    'world': 4560, # Worlds under Addons
}

_BEDROCK_URL_SEGMENTS = {
    'pack': 'mc-addons/resource-packs',
    'world': 'mc-addons/worlds',
}

_LOADER_NAMES = {
    'fabric': 'Fabric',
    'forge': 'Forge',
    'neoforge': 'NeoForge',
    'quilt': 'Quilt',
}

# Maps SPDX license IDs to the keys PU's curseforge.js license map uses
_SPDX_TO_PU = {
    'CC0-1.0': 'Public Domain',
    'CC-BY-4.0': 'Creative Commons 4.0',
    'CC-BY-SA-4.0': 'Creative Commons 4.0',
    'CC-BY-NC-4.0': 'Creative Commons 4.0',
    'CC-BY-NC-SA-4.0': 'Attribution-NonCommercial-ShareAlike 4.0 International',
    'CC-BY-ND-4.0': 'Creative Commons 4.0',
    'CC-BY-NC-ND-4.0': 'Creative Commons 4.0',
    'MIT': 'MIT License',
    'Apache-2.0': 'Apache License version 2.0',
    'GPL-2.0': 'GNU General Public License version 2 (GPLv2)',
    'GPL-3.0': 'GNU General Public License version 3 (GPLv3)',
    'LGPL-2.1': 'GNU Lesser General Public License version 2.1 (LGPLv2.1)',
    'LGPL-3.0': 'GNU Lesser General Public License version 3 (LGPLv3)',
    'AGPL-3.0': 'GNU Affero General Public License version 3 (AGPLv3)',
    'MPL-2.0': 'Mozilla Public License 2.0',
    'ISC': 'ISC License (ISCL)',
    'Zlib': 'zlib/libpng License',
}

_NAME_TO_SPDX = {
    name: spdx
    for spdx, name in _SPDX_TO_PU.items()
    if sum(1 for v in _SPDX_TO_PU.values() if v == name) == 1
}


class CurseForgeSite(Site):
    name = 'curseforge'
    aliases = ['cf']
    label = 'CurseForge'
    template_ext = '.html'
    desc_exts = ['.html', '.md']
    auth_arg = 'cf'
    required_auth_keys = {'token', 'cookie'}
    project_types = {'pack', 'mod', 'world'}

    _AUTH_URL = 'https://authors.curseforge.com'
    _REQUIRED_COOKIES = ('AuthorsUser', 'CobaltSession')

    def __init__(self):
        self._game_versions: dict[str, list[dict]] = {}

    # ── HTTP transport ─────────────────────────────────────────────────────────
    @staticmethod
    def _msg(body: str) -> str:
        try:
            return (json.loads(body).get('message') or '').lower()
        except (json.JSONDecodeError, AttributeError):
            return ''

    def classify_http_error(self, e: urllib.error.HTTPError) -> Exception:
        # CurseForge overloads 401/403/400: the JSON message decides auth vs generic.
        body = e.read().decode(errors='replace')
        if e.code in (401, 403):
            msg = self._msg(body)
            if msg and 'unauthorized' not in msg and 'forbidden' not in msg:
                return SiteError(e.code, body)
            return AuthExpiredError(e.code, body)
        if e.code == 400 and 'forbidden' in self._msg(body):
            return AuthExpiredError(e.code, body)
        return SiteError(e.code, body)

    @staticmethod
    def _headers(extra: dict) -> dict:
        return {
            'User-Agent': _UA,
            'Origin': 'https://authors.curseforge.com',
            'Referer': 'https://authors.curseforge.com/',
            **extra,
        }

    def _get(self, url: str, headers: dict) -> Any:
        return self._send(urllib.request.Request(url, headers=self._headers(headers)))

    def _json(self, url: str, headers: dict, body: dict, method: str = 'POST') -> Any:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(),
            headers=self._headers({**headers, 'Content-Type': 'application/json'}),
            method=method,
        )
        return self._send(req)

    def _post_json(self, url: str, headers: dict, body: dict) -> Any:
        return self._json(url, headers, body, method='POST')

    def _put_json(self, url: str, headers: dict, body: dict) -> Any:
        return self._json(url, headers, body, method='PUT')

    def _delete(self, url: str, headers: dict) -> None:
        self._send(urllib.request.Request(url, headers=self._headers(headers), method='DELETE'))

    def _post_multipart(self, url: str, headers: dict, fields: dict,
                        files: list[tuple[str, str, bytes, str]]) -> Any:
        boundary = b'----PuppyBoundary'
        parts = []
        for name, value in fields.items():
            parts.append(
                f'--{boundary.decode()}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
            )
        for field_name, filename, data, mime_type in files:
            parts.append(
                f'--{boundary.decode()}\r\nContent-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\nContent-Type: {mime_type}\r\n\r\n'.encode()
                + data + b'\r\n'
            )
        parts.append(f'--{boundary.decode()}--\r\n'.encode())
        req = urllib.request.Request(
            url, data=b''.join(parts),
            headers=self._headers({
                **headers,
                'Content-Type': f'multipart/form-data; boundary={boundary.decode()}',
            }),
            method='POST',
        )
        return self._send(req)

    def _download(self, url: str, dest: Path) -> None:
        req = urllib.request.Request(url, headers=self._headers({}))
        dest.write_bytes(urlopen_retrying(req, timeout=30))

    @staticmethod
    def _resolve_category_ids(names: list) -> tuple[int | None, list[int]]:
        ids = []
        for name in names:
            s = str(name)
            cid = _CATEGORIES_LOWER.get(s.lower()) or (int(s) if s.isdigit() else None)
            if cid is not None:
                ids.append(cid)
            else:
                raise SystemExit(f'Unknown curseforge category: {name!r}')
        return (ids[0] if ids else None, ids[1:])

    @staticmethod
    def _extract_id_from_page(html: str) -> int | None:
        m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                page_props = data.get('props', {}).get('pageProps', {})
                for key in ('project', 'mod', 'addon'):
                    obj = page_props.get(key)
                    if isinstance(obj, dict) and obj.get('id'):
                        return int(obj['id'])
                for val in page_props.values():
                    if isinstance(val, dict) and val.get('id') and isinstance(val.get('id'), int):
                        return int(val['id'])
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        for pattern in (r'"projectId"\s*:\s*(\d+)', r'"modId"\s*:\s*(\d+)', r'data-project-id="(\d+)"'):
            m = re.search(pattern, html)
            if m:
                return int(m.group(1))
        return None

    def _fetch_game_versions(self, auth: dict) -> list[dict]:
        token = auth.get('curseforge', {}).get('token', '')
        if token not in self._game_versions:
            self._game_versions[token] = self._get(f'{_API}/game/versions', {'X-Api-Token': token}) or []
        return self._game_versions[token]

    def _resolve_game_version_ids(self, version_strings: list[str], auth: dict) -> list[int]:
        name_to_id: dict[str, int] = {}
        for v in self._fetch_game_versions(auth):
            name_to_id.setdefault(v['name'], v['id'])
        return [name_to_id[vs] for vs in version_strings if vs in name_to_id]

    def has_credentials(self, auth: dict) -> bool:
        creds = auth.get('curseforge', {})
        return bool(creds.get('token') and creds.get('cookie'))

    def create_project(self, *, config, auth, icon_bytes, image_list, images_dir, verbosity):
        return self.create(config=config, auth=auth, icon_bytes=icon_bytes, verbosity=verbosity)

    def extract_cookies(self, ctx) -> tuple[str | None, str | None]:
        found = {c['name']: c['value'] for c in ctx.cookies([self._AUTH_URL])}
        missing = [n for n in self._REQUIRED_COOKIES if n not in found]
        if missing:
            names = ', '.join(found.keys()) or 'none'
            return None, self._login_error(f'found: {names}, missing: {", ".join(missing)}')
        return '; '.join(f'{n}={found[n]}' for n in self._REQUIRED_COOKIES), None

    def missing_token_warning(self, auth: dict) -> str | None:
        return self._token_warning(auth)

    def convert_md(self, text: str) -> str:
        return md_to_html(text)

    def spdx_license(self, value: str) -> str | None:
        return _NAME_TO_SPDX.get(value)

    def apply_neutral(self, config: dict) -> None:
        resolution = config.get('resolution')
        if resolution is not None:
            # The resolution tier is the CurseForge primary category for packs;
            # any explicit `category` entries become additional (sub)categories.
            sc = config.setdefault('curseforge', {})
            res_cat = f'{resolution}x'
            existing = sc.get('category')
            if existing is None:
                sc['category'] = res_cat
            else:
                rest = [existing] if isinstance(existing, str) else list(existing)
                sc['category'] = [res_cat] + [c for c in rest if c != res_cat]

        license_ = config.get('license')
        if license_:
            mapped = _SPDX_TO_PU.get(license_, license_)
            config.setdefault('curseforge', {}).setdefault('license', mapped)

        links = config.get('links') or {}
        if isinstance(links, dict) and links.get('home'):
            config.setdefault('curseforge', {}).setdefault('socials', {}).setdefault('website', links['home'])
        if isinstance(links, dict) and links.get('source'):
            config.setdefault('curseforge', {}).setdefault('links', {}).setdefault('source', links['source'])

        if isinstance(links, dict):
            # CurseForge holds only one donation link; the user picks which by
            # listing it first among the donation links in puppy.yaml.
            donation_keys = set(self._DONATION_LINK_KEYS)
            for key, value in links.items():
                if key in donation_keys and value:
                    dtype = 'github' if key == 'github_sponsors' else key
                    config.setdefault('curseforge', {}).setdefault(
                        'donation', {'type': dtype, 'value': value}
                    )
                    break

        socials = config.get('socials') or {}
        if isinstance(socials, dict):
            for key, value in socials.items():
                if value and key in _SOCIAL_TYPES:
                    config.setdefault('curseforge', {}).setdefault('socials', {}).setdefault(key, value)

    def preview_rows(self, sc: dict) -> list[tuple[str, str]]:
        rows = []
        if sc.get('category'):
            raw = sc['category']
            rows.append(('Category', ', '.join([raw] if isinstance(raw, str) else raw)))
        if sc.get('license'):
            rows.append(('License', str(sc['license'])))
        return rows

    _DONATION_LINK_KEYS = ['patreon', 'kofi', 'paypal', 'buyMeACoffee', 'github_sponsors', 'other']

    _SOCIAL_KEYS = [
        'bluesky', 'discord', 'facebook', 'github', 'instagram', 'mastodon',
        'patreon', 'pinterest', 'reddit', 'tiktok', 'twitch', 'twitter',
        'website', 'youtube',
    ]

    def apply_settings(self, settings: dict, sc: dict) -> None:
        entry = settings.setdefault('curseforge', {})
        donation = sc.get('donation') or {}
        entry['donation'] = {'type': donation.get('type'), 'value': donation.get('value')}
        configured_socials = sc.get('socials') or {}
        entry['socials'] = {k: configured_socials.get(k) for k in self._SOCIAL_KEYS}

    def auth_yaml_entry(self) -> str:
        return (
            'curseforge:\n'
            '  token: YOUR_CURSEFORGE_API_TOKEN\n'
            '  cookie: CobaltSession=YOUR_COBALT_SESSION_COOKIE\n'
        )

    def init_template(self) -> tuple[str, str]:
        return ('description.html', '<!-- CurseForge description (HTML) -->\n')

    def url_for(self, site_config: dict) -> str | None:
        ref = site_config.get('slug') or site_config.get('id')
        if not ref:
            return None
        project_type = site_config.get('type', 'pack')
        if site_config.get('bedrock'):
            segment = _BEDROCK_URL_SEGMENTS.get(project_type, 'mc-addons')
        else:
            segment = _URL_SEGMENTS.get(project_type, 'texture-packs')
        return f'https://www.curseforge.com/minecraft/{segment}/{ref}'

    def resolve_id(self, config: dict, auth: dict, verbosity: int) -> dict:
        sc = config.get('curseforge', {})
        if sc.get('id') or not sc.get('slug'):
            return config
        slug = sc['slug']
        cookie = auth.get('curseforge', {}).get('cookie', '')
        if cookie:
            # Try authors portal API (works for user's own projects)
            try:
                data = self._get(
                    f'{_DASH}/projects?search={urllib.parse.quote(slug)}',
                    self._cookie_headers(auth),
                )
                projects = data if isinstance(data, list) else (
                    data.get('data', []) if isinstance(data, dict) else []
                )
                match = next((p for p in projects if p.get('slug') == slug), None)
                if match and match.get('id'):
                    config = dict(config)
                    config['curseforge'] = dict(sc, id=int(match['id']))
                    if verbosity >= 1:
                        print(f"Resolved CurseForge ID for slug '{slug}': {match['id']}")
                    return config
            except AuthExpiredError:
                raise SystemExit(
                    f"Could not resolve CurseForge ID for slug '{slug}': "
                    f"auth expired — run: puppy auth --site cf"
                )
            except Exception as e:
                if verbosity >= 1:
                    print(f"  [CurseForge] authors API lookup failed (trying page scrape): {e}")
            # Try scraping the public project page
            project_type = config.get('type', 'pack')
            segments_to_try = [_URL_SEGMENTS.get(project_type, 'texture-packs')]
            if project_type == 'world':
                segments_to_try.append('mc-addons/worlds')
            elif project_type == 'pack':
                segments_to_try.append('mc-addons/resource-packs')
            page_headers = {'User-Agent': _UA, 'Cookie': cookie}
            for segment in segments_to_try:
                url = f'https://www.curseforge.com/minecraft/{segment}/{slug}'
                try:
                    req = urllib.request.Request(url, headers=page_headers)
                    page = urlopen_retrying(req, timeout=30).decode('utf-8', errors='replace')
                    project_id = self._extract_id_from_page(page)
                    if project_id:
                        config = dict(config)
                        config['curseforge'] = dict(sc, id=project_id)
                        if verbosity >= 1:
                            print(f"Resolved CurseForge ID for slug '{slug}': {project_id}")
                        return config
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        continue
                    raise SystemExit(f"Could not resolve CurseForge ID for slug '{slug}': {e}")
                except SystemExit:
                    raise
                except Exception as e:
                    raise SystemExit(f"Could not resolve CurseForge ID for slug '{slug}': {e}")
        raise SystemExit(
            f"Could not resolve CurseForge ID for slug '{slug}' — check the slug is correct. "
            f"Or set curseforge.id manually in puppy.yaml: "
            f"find it at https://authors.curseforge.com/projects/ (numeric ID in the URL when you open your project)."
        )

    def _cookie_headers(self, auth: dict) -> dict:
        return {'Cookie': auth.get('curseforge', {}).get('cookie', '')}

    def _token_headers(self, auth: dict) -> dict:
        return {'X-Api-Token': auth.get('curseforge', {}).get('token', '')}

    def fetch_project(self, project_id, auth: dict) -> dict:
        return self._get(f'{_DASH}/projects/{project_id}', self._cookie_headers(auth)) or {}

    def update_description(self, project_id, auth: dict, description: str) -> None:
        self._put_json(
            f'{_DASH}/projects/description/{project_id}',
            self._cookie_headers(auth),
            {'description': description, 'descriptionType': 1},
        )

    def upload_icon(self, project_id, auth: dict, icon_bytes: bytes) -> str:
        return self._post_multipart(
            f'{_DASH}/projects/{project_id}/upload-avatar',
            self._cookie_headers(auth),
            fields={'id': str(project_id)},
            files=[('file', 'pack.png', icon_bytes, 'image/png')],
        )

    def sync_gallery(self, project_id, auth: dict, images: list[dict], changed: set, verbosity: int = 0) -> None:
        h = self._cookie_headers(auth)
        params = urllib.parse.urlencode({
            'filter': '{}',
            'range': '[0,24]',
            'sort': '["id","DESC"]',
        })
        existing = self._get(f'{_DASH}/image-attachments/{project_id}?{params}', h) or []
        desired_filenames = {img['filename'] for img in images}
        existing_by_filename = {item['title']: item for item in existing if item.get('type') == 1}
        to_upload = [img for img in images if img['stem'] in changed]
        upload_filenames = {img['filename'] for img in to_upload}

        # delete images that were removed, or changed (deleted now, re-added below)
        for title, item in existing_by_filename.items():
            if title not in desired_filenames or title in upload_filenames:
                self._delete(f'{_DASH}/image-attachments/{project_id}/{item["id"]}/1', h)

        for img in to_upload:
            self._post_multipart(
                f'{_DASH}/image-attachments/image/{project_id}',
                h,
                fields={'id': str(project_id)},
                files=[('files', img['filename'], img['data'], img['mime_type'])],
            )

        if not to_upload:
            return
        uploaded = self._get(f'{_DASH}/image-attachments/{project_id}?{params}', h) or []
        uploaded_by_filename = {item['title']: item for item in uploaded}
        for img in to_upload:
            item = uploaded_by_filename.get(img['filename'])
            if item and item.get('id'):
                self._put_json(
                    f'{_DASH}/image-attachments/{project_id}',
                    h,
                    {
                        'id': item['id'],
                        'title': img.get('name', img['filename']),
                        'description': img.get('description', ''),
                        'isFeatured': img.get('featured', False),
                        'type': 1,
                    },
                )

    def update_details(self, project_id, auth: dict, sc: dict, avatar_url: str = None) -> None:
        h = self._cookie_headers(auth)
        socials = sc.get('socials') or {}
        donation = sc.get('donation') or {}
        dtype = donation.get('type', 'none')
        raw_cat = sc.get('category')
        if raw_cat is not None:
            cat_list = [raw_cat] if isinstance(raw_cat, (str, int)) else list(raw_cat)
            primary_from_cat, sub_cat_ids = self._resolve_category_ids(cat_list)
        else:
            primary_from_cat, sub_cat_ids = None, []
        details = {
            'name': sc.get('name', ''),
            'slug': sc.get('slug', ''),
            'summary': sc.get('summary', ''),
            'allowComments': True,
            'enableProjectPages': False,
            'avatarUrl': avatar_url or '',
            'donationTypeId': _DONATION_TYPES.get(dtype, -1),
            'donationIdentifier': '' if dtype == 'none' else donation.get('value', ''),
            'subCategoryIds': sub_cat_ids,
            'links': [
                {'type': _SOCIAL_TYPES[k], 'url': v}
                for k, v in socials.items()
                if v and k in _SOCIAL_TYPES
            ],
        }
        primary = primary_from_cat if primary_from_cat is not None else sc.get('mainCategory')
        if primary is not None:
            details['primaryCategoryId'] = primary
        self._put_json(f'{_DASH}/projects/{project_id}/update-details', h, details)

        license_name = sc.get('license')
        if license_name:
            license_id = _LICENSE_IDS.get(license_name)
            if license_id:
                self._put_json(
                    f'{_DASH}/project-license/{project_id}/update',
                    h,
                    {'licenseId': license_id},
                )

        links = sc.get('links') or {}
        source_url = links.get('source')
        if source_url:
            try:
                self._put_json(
                    f'{_DASH}/project-source/{project_id}/update',
                    h,
                    {
                        'sourceHostUrl': source_url,
                        'sourceHost': 3,
                        'packagerMode': 1,
                    },
                )
            except SiteError:
                pass

    def upload_file(
        self,
        project_id,
        auth: dict,
        pack_path: Path,
        version: str,
        config: dict,
    ) -> None:
        minecraft = config.get('minecraft')
        explicit_versions = config.get('versions', {})
        if minecraft:
            base = (
                {'type': 'exact', 'version': str(minecraft)}
                if not isinstance(minecraft, dict)
                else minecraft
            )
            spec = explicit_versions.get('curseforge', base)
        else:
            spec = explicit_versions.get('curseforge', {})
        version_strings = []
        if isinstance(spec, dict):
            v = spec.get('version') or spec.get('exact')
            if v:
                version_strings = [str(v)]
        elif isinstance(spec, str):
            version_strings = [spec]
        loaders = config.get('loaders') or []
        loader_names = [_LOADER_NAMES[ldr] for ldr in loaders if ldr in _LOADER_NAMES]
        game_version_ids = self._resolve_game_version_ids(version_strings + loader_names, auth)
        if config.get('client_side') in ('required', 'optional'):
            game_version_ids.append(_ENV_CLIENT)
        if config.get('server_side') in ('required', 'optional'):
            game_version_ids.append(_ENV_SERVER)

        slug = config.get('curseforge', {}).get('slug') or config.get('handle', '')
        metadata = {
            'changelog': config.get('changelog', ''),
            'changelogType': 'markdown',
            'displayName': f'{slug} v{version}',
            'gameVersions': game_version_ids,
            'releaseType': 'release',
        }
        artifact_bytes = pack_path.read_bytes()
        for attempt in range(3):
            try:
                self._post_multipart(
                    f'{_API}/projects/{project_id}/upload-file',
                    self._token_headers(auth),
                    fields={'metadata': json.dumps(metadata)},
                    files=[('file', pack_path.name, artifact_bytes, 'application/zip')],
                )
                break
            except AuthExpiredError as e:
                if attempt < 2 and not e.body.strip():
                    time.sleep(5)
                    continue
                raise

    def create(self, *, config: dict, auth: dict, icon_bytes: bytes, verbosity: int = 0) -> dict:
        import time
        h = self._cookie_headers(auth)

        avatar_url = self._post_multipart(
            f'{_DASH}/projects/game/432/upload-avatar',
            h,
            fields={},
            files=[('file', 'pack.png', icon_bytes, 'image/png')],
        )
        if not isinstance(avatar_url, str):
            raise SystemExit(f'CurseForge icon upload failed: {avatar_url}')
        if verbosity >= 1:
            print('  [CurseForge] icon uploaded')

        sc = config.get('curseforge', {})
        project_type = config.get('type', 'pack')
        bedrock = config.get('bedrock', False)
        class_id = _BEDROCK_CLASS_ID if bedrock else _CLASS_IDS.get(project_type, 12)
        default_cat = (
            _BEDROCK_DEFAULT_CATEGORIES.get(project_type, 4561)
            if bedrock else
            _DEFAULT_CATEGORIES.get(project_type, 393)
        )
        raw_cat = sc.get('category')
        if raw_cat is not None:
            cat_list = [raw_cat] if isinstance(raw_cat, str) else list(raw_cat)
            primary_cat_id, sub_cat_ids = self._resolve_category_ids(cat_list)
            if primary_cat_id is None:
                primary_cat_id = default_cat
        else:
            sub_cat_ids = []
            main_cat = sc.get('mainCategory')
            if main_cat is not None:
                cat_str = str(main_cat)
                if cat_str in _CATEGORIES:
                    primary_cat_id = _CATEGORIES[cat_str]
                elif cat_str.isdigit():
                    primary_cat_id = int(cat_str)
                else:
                    raise SystemExit(f'Unknown curseforge.mainCategory: {main_cat!r}')
            else:
                primary_cat_id = default_cat
        license_name = sc.get('license') or config.get('license') or 'All Rights Reserved'
        license_name = _SPDX_TO_PU.get(license_name, license_name)
        license_id = _LICENSE_IDS.get(license_name, 1)

        result = self._post_json(f'{_DASH}/projects', h, {
            'name': config.get('name', ''),
            'avatarUrl': avatar_url,
            'summary': config.get('summary', ''),
            'description': 'placeholder',
            'primaryCategoryId': primary_cat_id,
            'subCategoryIds': sub_cat_ids,
            'allowComments': True,
            'allowDistribution': False,
            'gameId': 432,
            'classId': class_id,
            'descriptionType': 1,
            'licenseId': license_id,
        })
        if not isinstance(result, dict) or 'id' not in result:
            raise SystemExit(f'CurseForge project creation failed: {result}')

        project_id = result['id']
        if verbosity >= 1:
            print(f'  [CurseForge] project created (id={project_id}), waiting for slug...')
        time.sleep(5)

        try:
            project_data = self._get(f'{_DASH}/projects/{project_id}', h) or {}
            if not isinstance(project_data, dict):
                project_data = {}
            slug = project_data.get('slug', '')

            result = {'id': project_id, 'slug': slug}
            if bedrock:
                result['bedrock'] = True
            if project_data.get('primaryCategoryId') is not None:
                result['category'] = project_data['primaryCategoryId']
            license_id_inv = {v: k for k, v in _LICENSE_IDS.items()}
            harvested_license = license_id_inv.get(project_data.get('licenseId'))
            if harvested_license:
                result['license'] = harvested_license

            social_inv = {v: k for k, v in _SOCIAL_TYPES.items()}
            socials = {
                social_inv[link['type']]: link['url']
                for link in (project_data.get('links') or [])
                if link.get('type') in social_inv and link.get('url')
            }
            if socials:
                result['socials'] = socials

            if verbosity >= 1:
                if bedrock:
                    segment = _BEDROCK_URL_SEGMENTS.get(project_type, 'mc-addons')
                else:
                    segment = _URL_SEGMENTS.get(project_type, 'texture-packs')
                print(f'  [CurseForge] https://www.curseforge.com/minecraft/{segment}/{slug}')
        except Exception as e:
            raise SystemExit(
                f'CurseForge project was created (id={project_id}) but slug lookup failed: {e}\n'
                f'Add curseforge:\n  id: {project_id}\nto puppy.yaml manually.'
            )
        return result

    def img_tag(self, url: str, name: str) -> str:
        return f'<img src="{url}" width="600" alt="{name}"><br>'

    def upload_artifact(self, project_id, auth: dict, zip_path: Path, version: str,
                        config: dict, puppy_dir: Path, verbosity: int) -> None:
        if verbosity >= 1:
            print(f'  [CurseForge] uploading version {version}')
        self.upload_file(project_id, auth, zip_path, version, config)
        self.post_upload(puppy_dir, version)

    def upload_images(self, project_id, auth: dict, image_list: list, images_dir: Path,
                      verbosity: int, project_type: str = 'pack', changed: set = None) -> dict[str, str]:
        if not image_list:
            return {}
        images = []
        for img_entry in image_list:
            src = find_image(img_entry['file'], images_dir)
            do = changed is None or src.stem in changed
            images.append({
                'filename': src.stem + '.jpg',
                'stem': src.stem,
                'data': prepare_gallery_image(src, verbosity=verbosity) if do else None,
                'mime_type': 'image/jpeg',
                'name': img_entry.get('name', ''),
                'description': img_entry.get('description', ''),
                'featured': img_entry.get('featured', False),
            })
        upload_set = {img['stem'] for img in images} if changed is None else changed
        if verbosity >= 1:
            print(f'  [CurseForge] syncing gallery ({len(upload_set)} changed)')
        self.sync_gallery(project_id, auth, images, upload_set, verbosity=verbosity)
        h = self._cookie_headers(auth)
        params = urllib.parse.urlencode({'filter': '{}', 'range': '[0,24]', 'sort': '["id","DESC"]'})
        gallery = self._get(f'{_DASH}/image-attachments/{project_id}?{params}', h) or []
        return {
            Path(item['title']).stem: item.get('imageUrl', '')
            for item in gallery
            if item.get('title') and item.get('imageUrl')
        }

    def gallery_urls(self, project_id, auth: dict, project_type: str = 'pack') -> dict[str, str]:
        h = self._cookie_headers(auth)
        params = urllib.parse.urlencode({'filter': '{}', 'range': '[0,24]', 'sort': '["id","DESC"]'})
        gallery = self._get(f'{_DASH}/image-attachments/{project_id}?{params}', h) or []
        return {
            Path(item['title']).stem: item.get('imageUrl', '')
            for item in gallery
            if item.get('title') and item.get('imageUrl')
        }

    def push(
        self,
        *,
        project_id,
        config: dict,
        description: str,
        auth: dict,
        verbosity: int,
        avatar_url: str = None,
    ) -> None:
        sc = {
            'name': config.get('name', ''),
            'summary': config.get('summary', ''),
            **config.get('curseforge', {}),
        }
        if sc.get('category') is None:
            remote = self.fetch_project(project_id, auth)
            if remote.get('primaryCategoryId'):
                sc['category'] = remote['primaryCategoryId']

        if verbosity >= 1:
            print('  [CurseForge] updating description')
        self.update_description(project_id, auth, description)

        if avatar_url is None:
            avatar_url = self.fetch_project(project_id, auth).get('avatarUrl', '')

        if verbosity >= 1:
            print('  [CurseForge] updating details')
        self.update_details(project_id, auth, sc, avatar_url=avatar_url)

    def pull(
        self,
        project_id,
        auth: dict,
        puppy_dir: Path,
        images: bool = True,
        verbosity: int = 0,
        project_type: str = 'pack',
    ) -> dict:
        if verbosity >= 1:
            print('  [CurseForge] fetching project')
        data = self.fetch_project(project_id, auth)
        if not data:
            raise SystemExit(f'Could not fetch CurseForge project: {project_id}')

        token = auth.get('curseforge', {}).get('token')
        if token:
            try:
                desc_req = urllib.request.Request(
                    f'https://api.curseforge.com/v1/mods/{project_id}/description',
                    headers={'X-Api-Token': token},
                )
                desc_data = json.loads(urlopen_retrying(desc_req, timeout=30))
                site_dir = puppy_dir / 'curseforge'
                site_dir.mkdir(parents=True, exist_ok=True)
                (site_dir / 'description.html').write_text(desc_data['data'])
            except urllib.error.HTTPError:
                pass

        h = self._cookie_headers(auth)
        params = urllib.parse.urlencode({
            'filter': '{}',
            'range': '[0,24]',
            'sort': '["id","DESC"]',
        })
        try:
            gallery = self._get(f'{_DASH}/image-attachments/{project_id}?{params}', h) or []
        except SiteError as e:
            if e.code == 404:
                gallery = []
            else:
                raise

        image_entries = []
        for item in gallery:
            title = item.get('title', '')
            if title:
                image_entries.append({'file': title, 'description': item.get('description', '')})

        if images:
            avatar_url = data.get('avatarUrl')
            if avatar_url:
                existing = [
                    p for p in puppy_dir.iterdir()
                    if p.suffix in ('.png', '.jpg', '.jpeg')
                    and p.name not in ('banner.png', 'logo.png')
                ]
                if not existing:
                    if verbosity >= 1:
                        print('  [CurseForge] downloading icon')
                    self._download(avatar_url, puppy_dir / 'pack.png')

            if gallery:
                images_dir = puppy_dir / 'images'
                images_dir.mkdir(parents=True, exist_ok=True)
                if verbosity >= 1:
                    print(f'  [CurseForge] downloading {len(gallery)} gallery images')
                for item in gallery:
                    url = item.get('imageUrl') or item.get('url', '')
                    title = item.get('title', '')
                    if url and title:
                        stem = Path(title).stem.strip('_')
                        suffix = Path(url.split('?')[0]).suffix or '.jpg'
                        self._download(url, images_dir / (stem + suffix))

        social_inv = {v: k for k, v in _SOCIAL_TYPES.items()}
        socials = {}
        for link in (data.get('links') or []):
            key = social_inv.get(link.get('type'))
            url = link.get('url')
            if key and url:
                socials[key] = url

        donation_inv = {v: k for k, v in _DONATION_TYPES.items()}
        dtype = donation_inv.get(data.get('donationTypeId'), 'none')
        donation = None
        if dtype and dtype != 'none':
            dval = data.get('donationIdentifier', '')
            if dval:
                donation = {'type': dtype, 'value': dval}

        license_id_inv = {v: k for k, v in _LICENSE_IDS.items()}
        license_name = license_id_inv.get(data.get('licenseId'))

        result: dict = {
            'id': data.get('id', project_id),
            'slug': data.get('slug'),
        }
        if data.get('classId') == _BEDROCK_CLASS_ID:
            result['bedrock'] = True
        if donation:
            result['donation'] = donation
        if data.get('primaryCategoryId') is not None:
            result['category'] = data['primaryCategoryId']
        if socials:
            result['socials'] = socials

        if license_name:
            result['license'] = license_name
        return {
            'config': {
                'name': data.get('name', ''),
                'summary': data.get('summary', ''),
                'images': image_entries,
            },
            'curseforge': result,
        }
