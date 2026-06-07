from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from puppy.errors import AuthExpiredError, SiteError
from puppy.images import find_image, prepare_gallery_image, prepare_icon
from puppy.renderer import md_to_html
from puppy.sites.base import Site


_CF_API = 'https://minecraft.curseforge.com/api'
_CF_DASH = 'https://authors.curseforge.com/_api'
_CF_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

_cf_game_versions_cache: dict[str, list[dict]] = {}


def _cf_fetch_game_versions(auth: dict) -> list[dict]:
    token = auth.get('curseforge', {}).get('token', '')
    if token not in _cf_game_versions_cache:
        result = _cf_get(f'{_CF_API}/game/versions', {'X-Api-Token': token})
        _cf_game_versions_cache[token] = result or []
    return _cf_game_versions_cache[token]


def _cf_resolve_game_version_ids(version_strings: list[str], auth: dict) -> list[int]:
    versions = _cf_fetch_game_versions(auth)
    name_to_id = {v['name']: v['id'] for v in versions}
    ids = []
    for vs in version_strings:
        vid = name_to_id.get(vs)
        if vid:
            ids.append(vid)
    return ids


def _cf_headers(extra: dict) -> dict:
    return {
        'User-Agent': _CF_UA,
        'Origin': 'https://authors.curseforge.com',
        'Referer': 'https://authors.curseforge.com/',
        **extra,
    }


def _cf_get(url: str, headers: dict) -> Any:
    req = urllib.request.Request(url, headers=_cf_headers(headers))
    return _cf_send(req)


def _cf_json(url: str, headers: dict, body: dict, method: str = 'POST') -> Any:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers=_cf_headers({**headers, 'Content-Type': 'application/json'}),
        method=method,
    )
    return _cf_send(req)


def _cf_post_json(url: str, headers: dict, body: dict) -> Any:
    return _cf_json(url, headers, body, method='POST')


def _cf_put_json(url: str, headers: dict, body: dict) -> Any:
    return _cf_json(url, headers, body, method='PUT')


def _cf_delete(url: str, headers: dict) -> None:
    req = urllib.request.Request(url, headers=_cf_headers(headers), method='DELETE')
    _cf_send(req)


def _cf_post_multipart(
    url: str,
    headers: dict,
    fields: dict,
    files: list[tuple[str, str, bytes, str]],
) -> Any:
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
    body = b''.join(parts)
    req = urllib.request.Request(
        url, data=body,
        headers=_cf_headers({
            **headers,
            'Content-Type': f'multipart/form-data; boundary={boundary.decode()}',
        }),
        method='POST',
    )
    return _cf_send(req)


def _cf_download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers=_cf_headers({}))
    with urllib.request.urlopen(req, timeout=30) as r:
        dest.write_bytes(r.read())


def _cf_send(req: urllib.request.Request) -> Any:
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            if not body:
                return None
            try:
                return json.loads(body)
            except (json.JSONDecodeError, ValueError):
                return body.decode()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        if e.code in (401, 403):
            try:
                msg = (json.loads(body).get('message') or '').lower()
                if msg and 'unauthorized' not in msg and 'forbidden' not in msg:
                    raise SiteError(e.code, body)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise AuthExpiredError(e.code, body)
        raise SiteError(e.code, body)


_CF_LICENSE_IDS = {
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

_CF_DONATION_TYPES = {
    'none': -1, 'paypal': 1, 'paypalHosted': 2, 'patreon': 6,
    'github': 7, 'kofi': 8, 'buyMeACoffee': 9,
}

_CF_SOCIAL_TYPES = {
    'mastodon': 1, 'discord': 2, 'website': 3, 'facebook': 4, 'twitter': 5,
    'instagram': 6, 'patreon': 7, 'twitch': 8, 'reddit': 9, 'youtube': 10,
    'tiktok': 11, 'pinterest': 12, 'github': 13, 'bluesky': 14,
}

_CF_CATEGORIES = {
    '16x': 393, '32x': 394, '64x': 395, '128x': 396, '256x': 397,
    '512x and Higher': 398, 'Data Packs': 5193, 'Font Packs': 5244,
}

_CF_ENV_CLIENT = 9638
_CF_ENV_SERVER = 9639

# Maps SPDX license IDs to the keys PU's curseforge.js license map uses
_SPDX_TO_PU_CF = {
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


class CurseForgeSite(Site):
    name = 'curseforge'
    aliases = ['cf']
    label = 'CurseForge'
    template_ext = '.html'
    desc_exts = ['.html', '.md']
    supported_types = frozenset({'pack'})

    def convert_md(self, text: str) -> str:
        return md_to_html(text)

    def apply_neutral(self, config: dict) -> None:
        resolution = config.get('resolution')
        if resolution is not None:
            config.setdefault('curseforge', {}).setdefault('mainCategory', f'{resolution}x')

        license_ = config.get('license')
        if license_:
            cf_license = _SPDX_TO_PU_CF.get(license_, license_)
            config.setdefault('curseforge', {}).setdefault('license', cf_license)

        links = config.get('links') or {}
        if isinstance(links, dict) and links.get('home'):
            config.setdefault('curseforge', {}).setdefault('socials', {}).setdefault('website', links['home'])

        if isinstance(links, dict):
            for key in self._DONATION_LINK_KEYS:
                if links.get(key):
                    cf_key = 'github' if key == 'github_sponsors' else key
                    config.setdefault('curseforge', {}).setdefault(
                        'donation', {'type': cf_key, 'value': links[key]}
                    )
                    break

    def preview_rows(self, sc: dict) -> list[tuple[str, str]]:
        rows = []
        if sc.get('mainCategory'):
            rows.append(('Main Category', str(sc['mainCategory'])))
        extra = {k: v for k, v in sc.get('additionalCategories', {}).items() if v}
        if extra:
            rows.append(('Categories', ', '.join(extra)))
        if sc.get('license'):
            rows.append(('License', str(sc['license'])))
        return rows

    def needs_upload(self, site_id, auth: dict, zip_path: Path, version: str, project) -> bool:
        local_size = zip_path.stat().st_size
        cf_auth = auth.get('curseforge', {})
        params = urllib.parse.urlencode({
            'filter': json.dumps({'projectId': site_id}),
            'range': '[0, 0]',
            'sort': '["DateCreated", "DESC"]',
        })
        req = urllib.request.Request(
            f'https://authors.curseforge.com/_api/project-files?{params}',
            headers=_cf_headers({
                'Cookie': cf_auth.get('cookie', ''),
                'Content-Type': 'application/json',
            }),
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            files = json.loads(r.read())
        if not files:
            return True
        latest = files[0]
        return not (
            latest.get('size') == local_size
            and f'v{version}' in latest.get('displayName', '')
        )

    _DONATION_LINK_KEYS = ['patreon', 'kofi', 'paypal', 'buyMeACoffee', 'github_sponsors', 'other']

    _SOCIAL_KEYS = [
        'bluesky', 'discord', 'facebook', 'github', 'instagram', 'mastodon',
        'patreon', 'pinterest', 'reddit', 'tiktok', 'twitch', 'twitter',
        'website', 'youtube',
    ]

    def apply_settings(self, settings: dict, sc: dict) -> None:
        cf = settings.setdefault('curseforge', {})
        donation = sc.get('donation') or {}
        cf['donation'] = {'type': donation.get('type'), 'value': donation.get('value')}
        configured_socials = sc.get('socials') or {}
        cf['socials'] = {k: configured_socials.get(k) for k in self._SOCIAL_KEYS}

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
        return f'https://www.curseforge.com/minecraft/texture-packs/{ref}'

    def _cookie_headers(self, auth: dict) -> dict:
        return {'Cookie': auth.get('curseforge', {}).get('cookie', '')}

    def _token_headers(self, auth: dict) -> dict:
        return {'X-Api-Token': auth.get('curseforge', {}).get('token', '')}

    def fetch_project(self, project_id, auth: dict) -> dict:
        return _cf_get(f'{_CF_DASH}/projects/{project_id}', self._cookie_headers(auth)) or {}

    def update_description(self, project_id, auth: dict, description: str) -> None:
        _cf_put_json(
            f'{_CF_DASH}/projects/description/{project_id}',
            self._cookie_headers(auth),
            {'description': description, 'descriptionType': 1},
        )

    def upload_icon(self, project_id, auth: dict, icon_bytes: bytes) -> str:
        return _cf_post_multipart(
            f'{_CF_DASH}/projects/{project_id}/upload-avatar',
            self._cookie_headers(auth),
            fields={'id': str(project_id)},
            files=[('file', 'pack.png', icon_bytes, 'image/png')],
        )

    def sync_gallery(self, project_id, auth: dict, images: list[dict]) -> None:
        h = self._cookie_headers(auth)
        params = urllib.parse.urlencode({
            'filter': '{}',
            'range': '[0,24]',
            'sort': '["id","DESC"]',
        })
        existing = _cf_get(f'{_CF_DASH}/image-attachments/image/{project_id}?{params}', h) or []
        desired_filenames = {img['filename'] for img in images}
        existing_by_filename = {item['title']: item for item in existing}

        for title, item in existing_by_filename.items():
            if title not in desired_filenames:
                _cf_delete(f'{_CF_DASH}/image-attachments/{project_id}/{item["id"]}/1', h)

        for img in images:
            if img['filename'] not in existing_by_filename:
                result = _cf_post_multipart(
                    f'{_CF_DASH}/image-attachments/image/{project_id}',
                    h,
                    fields={},
                    files=[('image', img['filename'], img['data'], img['mime_type'])],
                )
                if result and result.get('id'):
                    _cf_put_json(
                        f'{_CF_DASH}/image-attachments/{result["id"]}',
                        h,
                        {'title': img['filename'], 'description': img.get('description', '')},
                    )

    def update_details(self, project_id, auth: dict, sc: dict, avatar_url: str = None) -> None:
        h = self._cookie_headers(auth)
        socials = sc.get('socials') or {}
        donation = sc.get('donation') or {}
        dtype = donation.get('type', 'none')
        details = {
            'name': sc.get('name', ''),
            'slug': sc.get('slug', ''),
            'summary': sc.get('summary', ''),
            'allowComments': True,
            'enableProjectPages': False,
            'avatarUrl': avatar_url or '',
            'donationTypeId': _CF_DONATION_TYPES.get(dtype, -1),
            'donationIdentifier': '' if dtype == 'none' else donation.get('value', ''),
            'subCategoryIds': [],
            'links': [
                {'type': _CF_SOCIAL_TYPES[k], 'url': v}
                for k, v in socials.items()
                if v and k in _CF_SOCIAL_TYPES
            ],
        }
        primary = sc.get('mainCategory')
        if primary is not None:
            details['primaryCategoryId'] = primary
        _cf_put_json(f'{_CF_DASH}/projects/{project_id}/update-details', h, details)

        license_name = sc.get('license')
        if license_name:
            license_id = _CF_LICENSE_IDS.get(license_name)
            if license_id:
                _cf_put_json(
                    f'{_CF_DASH}/project-license/{project_id}/update',
                    h,
                    {'licenseId': license_id},
                )

        links = sc.get('links') or {}
        source_url = links.get('source')
        if source_url:
            _cf_put_json(
                f'{_CF_DASH}/project-source/{project_id}/update',
                h,
                {
                    'sourceHostUrl': source_url,
                    'sourceHost': 3,
                    'packagerMode': 1,
                },
            )

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
            cf_versions = explicit_versions.get('curseforge', base)
        else:
            cf_versions = explicit_versions.get('curseforge', {})
        version_strings = []
        if isinstance(cf_versions, dict):
            v = cf_versions.get('version') or cf_versions.get('exact')
            if v:
                version_strings = [str(v)]
        elif isinstance(cf_versions, str):
            version_strings = [cf_versions]
        game_version_ids = _cf_resolve_game_version_ids(version_strings, auth)
        if config.get('client_side') in ('required', 'optional'):
            game_version_ids.append(_CF_ENV_CLIENT)
        if config.get('server_side') in ('required', 'optional'):
            game_version_ids.append(_CF_ENV_SERVER)

        slug = config.get('curseforge', {}).get('slug') or config.get('pack', '')
        metadata = {
            'changelog': config.get('changelog', ''),
            'changelogType': 'markdown',
            'displayName': f'{slug} v{version}',
            'gameVersions': game_version_ids,
            'releaseType': 'release',
        }
        artifact_bytes = pack_path.read_bytes()
        _cf_post_multipart(
            f'{_CF_API}/projects/{project_id}/upload-file',
            self._token_headers(auth),
            fields={'metadata': json.dumps(metadata)},
            files=[('file', pack_path.name, artifact_bytes, 'application/zip')],
        )

    def create(self, *, config: dict, auth: dict, icon_bytes: bytes, verbosity: int = 0) -> dict:
        import time
        h = self._cookie_headers(auth)

        avatar_url = _cf_post_multipart(
            f'{_CF_DASH}/projects/game/432/upload-avatar',
            h,
            fields={},
            files=[('file', 'pack.png', icon_bytes, 'image/png')],
        )
        if not isinstance(avatar_url, str):
            raise SystemExit(f'CurseForge icon upload failed: {avatar_url}')
        if verbosity >= 1:
            print('  [CurseForge] icon uploaded')

        sc = config.get('curseforge', {})
        main_cat = sc.get('mainCategory')
        primary_cat_id = _CF_CATEGORIES.get(str(main_cat), 393) if main_cat else 393
        license_name = sc.get('license') or config.get('license') or 'All Rights Reserved'
        license_id = _CF_LICENSE_IDS.get(license_name, 1)

        result = _cf_post_json(f'{_CF_DASH}/projects', h, {
            'name': config.get('name', ''),
            'avatarUrl': avatar_url,
            'summary': config.get('summary', ''),
            'description': 'placeholder',
            'primaryCategoryId': primary_cat_id,
            'subCategoryIds': [],
            'allowComments': True,
            'allowDistribution': False,
            'gameId': 432,
            'classId': 12,
            'descriptionType': 1,
            'licenseId': license_id,
        })
        if not isinstance(result, dict) or 'id' not in result:
            raise SystemExit(f'CurseForge project creation failed: {result}')

        project_id = result['id']
        if verbosity >= 1:
            print(f'  [CurseForge] project created (id={project_id}), waiting for slug...')
        time.sleep(5)

        project_data = _cf_get(f'{_CF_DASH}/projects/{project_id}', h) or {}
        if not isinstance(project_data, dict):
            project_data = {}
        slug = project_data.get('slug', '')

        result = {'id': project_id, 'slug': slug}
        if project_data.get('primaryCategoryId') is not None:
            result['mainCategory'] = project_data['primaryCategoryId']
        license_id_inv = {v: k for k, v in _CF_LICENSE_IDS.items()}
        harvested_license = license_id_inv.get(project_data.get('licenseId'))
        if harvested_license:
            result['license'] = harvested_license

        social_inv = {v: k for k, v in _CF_SOCIAL_TYPES.items()}
        socials = {
            social_inv[link['type']]: link['url']
            for link in (project_data.get('links') or [])
            if link.get('type') in social_inv and link.get('url')
        }
        if socials:
            result['socials'] = socials

        if verbosity >= 1:
            print(f'  [CurseForge] https://www.curseforge.com/minecraft/texture-packs/{slug}')
        return result

    def img_tag(self, url: str, name: str) -> str:
        return f'<img src="{url}" width="600" alt="{name}"><br>'

    def upload_images(self, project_id, auth: dict, image_list: list, images_dir: Path, verbosity: int) -> dict[str, str]:
        if not image_list:
            return {}
        images = []
        for img_entry in image_list:
            src = find_image(img_entry['file'], images_dir)
            data = prepare_gallery_image(src, verbosity=verbosity)
            images.append({
                'filename': src.stem + '.jpg',
                'data': data,
                'mime_type': 'image/jpeg',
            })
        if verbosity >= 1:
            print(f'  [CurseForge] syncing gallery ({len(images)} images)')
        self.sync_gallery(project_id, auth, images)
        h = self._cookie_headers(auth)
        params = urllib.parse.urlencode({'filter': '{}', 'range': '[0,24]', 'sort': '["id","DESC"]'})
        gallery = _cf_get(f'{_CF_DASH}/image-attachments/image/{project_id}?{params}', h) or []
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
        icon_path: Path,
        logo_path: Path,
        banner_path: Path,
        image_list: list,
        images_dir: Path,
        auth: dict,
        verbosity: int,
        pack_path: Path = None,
        version: str = None,
        force: bool = False,
    ) -> None:
        sc = {
            'name': config.get('name', ''),
            'summary': config.get('summary', ''),
            **config.get('curseforge', {}),
        }
        if sc.get('mainCategory') is None:
            remote = self.fetch_project(project_id, auth)
            if remote.get('primaryCategoryId'):
                sc['mainCategory'] = remote['primaryCategoryId']

        if verbosity >= 1:
            print(f'  [CurseForge] updating description')
        self.update_description(project_id, auth, description)

        if verbosity >= 1:
            print(f'  [CurseForge] uploading icon')
        icon_bytes = prepare_icon(icon_path, verbosity=verbosity)
        avatar_url = self.upload_icon(project_id, auth, icon_bytes)

        images = []
        for img_entry in image_list:
            src = find_image(img_entry['file'], images_dir)
            data = prepare_gallery_image(src, verbosity=verbosity)
            images.append({
                'filename': src.stem + '.jpg',
                'data': data,
                'mime_type': 'image/jpeg',
            })
        if images:
            if verbosity >= 1:
                print(f'  [CurseForge] syncing gallery ({len(images)} images)')
            self.sync_gallery(project_id, auth, images)

        if verbosity >= 1:
            print(f'  [CurseForge] updating details')
        self.update_details(project_id, auth, sc, avatar_url=avatar_url)

        if pack_path and version:
            if verbosity >= 1:
                print(f'  [CurseForge] uploading file v{version}')
            self.upload_file(project_id, auth, pack_path, version, config)

    def pull(
        self,
        project_id,
        auth: dict,
        puppy_dir: Path,
        images: bool = True,
        verbosity: int = 0,
    ) -> dict:
        if verbosity >= 1:
            print('  [CurseForge] fetching project')
        data = self.fetch_project(project_id, auth)
        if not data:
            raise SystemExit(f'Could not fetch CurseForge project: {project_id}')

        token = auth.get('curseforge', {}).get('token')
        if token:
            desc_req = urllib.request.Request(
                f'https://api.curseforge.com/v1/mods/{project_id}/description',
                headers={'x-api-key': token},
            )
            with urllib.request.urlopen(desc_req, timeout=30) as resp:
                desc_data = json.loads(resp.read())
            site_dir = puppy_dir / 'curseforge'
            site_dir.mkdir(parents=True, exist_ok=True)
            (site_dir / 'description.html').write_text(desc_data['data'])

        h = self._cookie_headers(auth)
        params = urllib.parse.urlencode({
            'filter': '{}',
            'range': '[0,24]',
            'sort': '["id","DESC"]',
        })
        gallery = _cf_get(f'{_CF_DASH}/image-attachments/image/{project_id}?{params}', h) or []

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
                    _cf_download(avatar_url, puppy_dir / 'pack.png')

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
                        _cf_download(url, images_dir / (stem + suffix))

        social_inv = {v: k for k, v in _CF_SOCIAL_TYPES.items()}
        socials = {}
        for link in (data.get('links') or []):
            key = social_inv.get(link.get('type'))
            url = link.get('url')
            if key and url:
                socials[key] = url

        donation_inv = {v: k for k, v in _CF_DONATION_TYPES.items()}
        dtype = donation_inv.get(data.get('donationTypeId'), 'none')
        donation = None
        if dtype and dtype != 'none':
            dval = data.get('donationIdentifier', '')
            if dval:
                donation = {'type': dtype, 'value': dval}

        license_id_inv = {v: k for k, v in _CF_LICENSE_IDS.items()}
        license_name = license_id_inv.get(data.get('licenseId'))

        cf_result: dict = {
            'id': data.get('id', project_id),
            'slug': data.get('slug'),
        }
        if donation:
            cf_result['donation'] = donation
        if license_name:
            cf_result['license'] = license_name
        if data.get('primaryCategoryId') is not None:
            cf_result['mainCategory'] = data['primaryCategoryId']
        if socials:
            cf_result['socials'] = socials

        return {
            'config': {
                'name': data.get('name', ''),
                'summary': data.get('summary', ''),
                'images': image_entries,
            },
            'curseforge': cf_result,
        }
