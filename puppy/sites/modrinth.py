from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from puppy.errors import AuthExpiredError, SiteError
from puppy.images import find_image, prepare_gallery_image, prepare_icon
from puppy.sites.base import Site


_MR_API = 'https://api.modrinth.com/v2'
_MR_UA = 'puppy/1.0'

_MR_TYPE_MAP = {
    'pack': 'resourcepack',
    'mod': 'mod',
    'world': 'world',
}

_MR_RESOLUTION_TIERS = frozenset({'8x-', '16x', '32x', '48x', '64x', '128x', '256x', '512x+'})


def _mr_headers(auth: dict, extra: dict = None) -> dict:
    h = {'User-Agent': _MR_UA}
    token = auth.get('modrinth', {}).get('token', '')
    if token:
        h['Authorization'] = token
    if extra:
        h.update(extra)
    return h


def _mr_send(req: urllib.request.Request) -> Any:
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
        if e.code == 401:
            raise AuthExpiredError(e.code, body)
        raise SiteError(e.code, body)


def _mr_get(url: str, auth: dict) -> Any:
    return _mr_send(urllib.request.Request(url, headers=_mr_headers(auth)))


def _mr_patch_json(url: str, auth: dict, body: dict) -> Any:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers=_mr_headers(auth, {'Content-Type': 'application/json'}),
        method='PATCH',
    )
    return _mr_send(req)


def _mr_patch_raw(url: str, auth: dict, data: bytes, mime: str) -> Any:
    req = urllib.request.Request(
        url, data=data,
        headers=_mr_headers(auth, {'Content-Type': mime}),
        method='PATCH',
    )
    return _mr_send(req)


def _mr_post_raw(url: str, auth: dict, data: bytes, mime: str) -> Any:
    req = urllib.request.Request(
        url, data=data,
        headers=_mr_headers(auth, {'Content-Type': mime}),
        method='POST',
    )
    return _mr_send(req)


def _mr_delete(url: str, auth: dict) -> None:
    _mr_send(urllib.request.Request(url, headers=_mr_headers(auth), method='DELETE'))


def _mr_post_multipart(url: str, auth: dict, fields: dict, files: list) -> Any:
    boundary = b'----PuppyMRBoundary'
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary.decode()}\r\nContent-Disposition: form-data; name="{name}"\r\nContent-Type: application/json\r\n\r\n{value}\r\n'.encode()
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
        headers=_mr_headers(auth, {'Content-Type': f'multipart/form-data; boundary={boundary.decode()}'}),
        method='POST',
    )
    return _mr_send(req)


def _mr_download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={'User-Agent': _MR_UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        dest.write_bytes(r.read())


def _mr_resolve_game_versions(spec: dict, auth: dict) -> list[str]:
    if not spec:
        return []
    version_type = spec.get('type', 'exact')
    if version_type == 'exact':
        v = spec.get('version') or spec.get('exact')
        return [str(v)] if v else []
    include_snapshots = spec.get('snapshots', False)
    all_versions = _mr_get(f'{_MR_API}/tag/game_version', auth) or []
    def _accepted(v: dict) -> bool:
        return include_snapshots or v.get('version_type') == 'release'
    accepted = [v['version'] for v in all_versions if _accepted(v)]
    if version_type == 'latest':
        return [accepted[0]] if accepted else []
    if version_type in ('range', 'between'):
        from_v = spec.get('from') or spec.get('start', '')
        to_v = spec.get('to') or spec.get('end', '')
        return [v for v in accepted if (not from_v or v >= from_v) and (not to_v or v <= to_v)]
    if version_type == 'since':
        from_v = spec.get('version') or spec.get('from', '')
        return [v for v in accepted if not from_v or v >= from_v]
    return []


def _mr_normalize_resolution(value) -> list[str]:
    items = [value] if not isinstance(value, list) else value
    return [f'{r}x' if str(r).isdigit() else str(r) for r in items]


_mr_category_header_cache: dict[str, str] = {}


def _mr_category_headers(auth: dict) -> dict[str, str]:
    global _mr_category_header_cache
    if not _mr_category_header_cache:
        cats = _mr_get(f'{_MR_API}/tag/category', auth)
        if isinstance(cats, list):
            _mr_category_header_cache = {c['name']: c['header'] for c in cats}
    return _mr_category_header_cache


def _mr_build_categories(sc: dict, config: dict, auth: dict) -> tuple[list[str], list[str]]:
    resolution = sc.get('resolution') if sc.get('resolution') is not None else config.get('resolution')
    resolution_cats = _mr_normalize_resolution(resolution) if resolution is not None else []
    raw = sc.get('category')
    content_cats = []
    if raw is not None:
        for c in ([raw] if isinstance(raw, str) else list(raw)):
            if c not in content_cats:
                content_cats.append(c)
    headers = _mr_category_headers(auth)
    primary = [c for c in content_cats if headers.get(c) == 'categories']
    additional = [c for c in content_cats if headers.get(c) != 'categories'] + resolution_cats
    return primary, additional


# Reverse map: Modrinth donation platform id → puppy key
_MR_DONATION_ID_TO_KEY = {
    'patreon': 'patreon',
    'ko-fi': 'kofi',
    'paypal': 'paypal',
    'buy-me-a-coffee': 'buyMeACoffee',
    'github-sponsors': 'github',
    'other': 'other',
}



class ModrinthSite(Site):
    name = 'modrinth'
    aliases = ['mr']
    label = 'Modrinth'
    template_ext = '.md'
    desc_exts = ['.md']

    def apply_neutral(self, config: dict) -> None:
        resolution = config.get('resolution')
        if resolution is not None:
            neutral_tier = f'{resolution}x'
            mr = config.setdefault('modrinth', {})
            existing = mr.get('resolution')
            if existing is None:
                mr['resolution'] = neutral_tier
            else:
                existing_list = _mr_normalize_resolution(existing)
                if neutral_tier not in existing_list:
                    print(f'warning: adding {neutral_tier} from neutral resolution to modrinth.resolution')
                    mr['resolution'] = existing_list + [neutral_tier]

        license_ = config.get('license')
        if license_:
            config.setdefault('modrinth', {}).setdefault('license', license_)

        links = config.get('links') or {}
        if isinstance(links, dict):
            donation = {
                mr_key: links[link_key]
                for link_key, mr_key in self._LINKS_TO_MR_DONATION.items()
                if links.get(link_key)
            }
            if donation:
                config.setdefault('modrinth', {}).setdefault('donation', donation)

        socials = config.get('socials') or {}
        if isinstance(socials, dict) and socials.get('discord'):
            config.setdefault('modrinth', {}).setdefault('discord', socials['discord'])

    def preview_rows(self, sc: dict) -> list[tuple[str, str]]:
        rows = []
        resolution = sc.get('resolution')
        if resolution is not None:
            rows.append(('Resolution', ', '.join(_mr_normalize_resolution(resolution))))
        if sc.get('category'):
            raw = sc['category']
            rows.append(('Category', ', '.join([raw] if isinstance(raw, str) else raw)))
        if sc.get('license'):
            rows.append(('License', str(sc['license'])))
        return rows

    def needs_upload(self, site_id, auth: dict, zip_path: Path, version: str, project) -> bool:
        local_hash = hashlib.sha512(zip_path.read_bytes()).hexdigest()
        headers = {'User-Agent': 'puppy/1.0'}
        token = auth.get('modrinth', {}).get('token', '')
        if token:
            headers['Authorization'] = token
        req = urllib.request.Request(
            f'https://api.modrinth.com/v2/project/{site_id}/version',
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            versions = json.loads(r.read())
        for v in versions:
            for f in v.get('files', []):
                if f.get('hashes', {}).get('sha512') == local_hash:
                    return False
        return True

    def upload_version(
        self,
        project_id: str,
        auth: dict,
        zip_path: Path,
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
            mr_spec = explicit_versions.get('modrinth', base)
        else:
            mr_spec = explicit_versions.get('modrinth', {})

        game_versions = _mr_resolve_game_versions(mr_spec, auth)
        slug = config.get('modrinth', {}).get('slug') or config.get('handle', '')
        project_type = config.get('type', 'pack')
        loaders = config.get('loaders')
        if not loaders:
            if project_type == 'pack':
                loaders = ['minecraft']
            else:
                raise SystemExit(
                    f'Modrinth upload requires loaders: set it in puppy.yaml '
                    f'(for example loaders: [fabric])'
                )
        version_data = {
            'name': f'{slug} v{version}',
            'version_number': version,
            'changelog': config.get('changelog', ''),
            'dependencies': [],
            'game_versions': game_versions,
            'version_type': 'release',
            'loaders': loaders,
            'featured': True,
            'project_id': project_id,
            'file_parts': ['file'],
            'primary_file': 'file',
        }
        zip_bytes = zip_path.read_bytes()
        _mr_post_multipart(
            f'{_MR_API}/version',
            auth,
            fields={'data': json.dumps(version_data)},
            files=[('file', zip_path.name, zip_bytes, 'application/zip')],
        )

    def resolve_id(self, config: dict, auth: dict, verbosity: int) -> dict:
        mr = config.get('modrinth', {})
        if mr.get('id') or not mr.get('slug'):
            return config
        slug = mr['slug']
        try:
            headers = {'User-Agent': 'puppy/1.0'}
            token = auth.get('modrinth', {}).get('token', '')
            if token:
                headers['Authorization'] = token
            req = urllib.request.Request(
                f'https://api.modrinth.com/v2/project/{slug}',
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
            config = dict(config)
            config['modrinth'] = dict(mr, id=data['id'], slug=data['slug'])
            if verbosity >= 1:
                print(f"Resolved Modrinth ID for slug '{slug}': {data['id']}")
        except Exception as e:
            raise SystemExit(f"Could not resolve Modrinth ID for slug '{slug}': {e}")
        return config

    _LINKS_TO_MR_DONATION = {
        'patreon': 'patreon',
        'kofi': 'kofi',
        'paypal': 'paypal',
        'buyMeACoffee': 'buyMeACoffee',
        'github_sponsors': 'github',
        'other': 'other',
    }

    _DONATION_KEYS = ['buyMeACoffee', 'github', 'kofi', 'other', 'patreon', 'paypal']

    _MR_DONATION_PLATFORMS = {
        'patreon': ('patreon', 'Patreon'),
        'kofi': ('ko-fi', 'Ko-fi'),
        'paypal': ('paypal', 'PayPal'),
        'buyMeACoffee': ('buy-me-a-coffee', 'Buy Me A Coffee'),
        'github': ('github-sponsors', 'GitHub Sponsors'),
        'other': ('other', 'Other'),
    }

    def create(self, *, config: dict, auth: dict, verbosity: int = 0) -> dict:
        mr = config.get('modrinth', {})
        base_slug = mr.get('slug') or config.get('handle', '')
        slug = base_slug
        suffix = 0
        while True:
            try:
                _mr_get(f'{_MR_API}/project/{slug}', auth)
                suffix += 1
                slug = f'{base_slug}-{suffix}'
            except SiteError as e:
                if e.code == 404:
                    break
                raise
        if suffix and verbosity >= 1:
            print(f'  [Modrinth] slug "{base_slug}" taken, using "{slug}"')

        license_id = config.get('license') or mr.get('license') or 'LicenseRef-All-Rights-Reserved'
        categories, additional_categories = _mr_build_categories(mr, config, auth)
        links = config.get('links') or {}
        socials = config.get('socials') or {}

        project_data = {
            'slug': slug,
            'title': config.get('name', ''),
            'description': config.get('summary', ''),
            'categories': categories,
            'additional_categories': additional_categories,
            'client_side': config.get('client_side', 'required'),
            'server_side': config.get('server_side', 'unsupported'),
            'body': '',
            'issues_url': links.get('issues') or None,
            'source_url': links.get('source') or None,
            'discord_url': socials.get('discord') or None,
            'license_id': license_id,
            'type': _MR_TYPE_MAP.get(config.get('type', 'pack'), 'resourcepack'),
            'is_draft': True,
            'initial_versions': [],
        }
        r = _mr_post_multipart(
            f'{_MR_API}/project',
            auth,
            fields={'data': json.dumps(project_data)},
            files=[],
        )
        if not isinstance(r, dict) or r.get('error'):
            raise SystemExit(f'Modrinth project creation failed: {r}')

        if verbosity >= 1:
            print(f'  [Modrinth] project created: https://modrinth.com/project/{r["slug"]}')
        return {'id': r['id'], 'slug': r['slug']}

    def upload_icon(self, project_id: str, auth: dict, icon_bytes: bytes) -> None:
        _mr_patch_raw(f'{_MR_API}/project/{project_id}/icon?ext=png', auth, icon_bytes, 'image/png')

    def sync_gallery(self, project_id: str, auth: dict, images: list[dict]) -> None:
        project = _mr_get(f'{_MR_API}/project/{project_id}', auth) or {}
        existing = project.get('gallery') or []
        desired_filenames = {img['filename'] for img in images}
        existing_by_filename = {item['title']: item for item in existing}

        for title, item in existing_by_filename.items():
            if title not in desired_filenames:
                params = urllib.parse.urlencode({'url': item['url']})
                _mr_delete(f'{_MR_API}/project/{project_id}/gallery?{params}', auth)

        for i, img in enumerate(images):
            if img['filename'] not in existing_by_filename:
                ext = 'jpg' if img['mime_type'] == 'image/jpeg' else 'png'
                params = urllib.parse.urlencode({
                    'ext': ext,
                    'featured': 'true' if img.get('featured') else 'false',
                    'title': img['filename'],
                    'description': img.get('description', ''),
                    'ordering': i,
                })
                _mr_post_raw(
                    f'{_MR_API}/project/{project_id}/gallery?{params}',
                    auth, img['data'], img['mime_type'],
                )

    def update_project(self, project_id: str, auth: dict, sc: dict, description: str, config: dict) -> None:
        links = config.get('links') or {}
        donation = sc.get('donation') or {}
        categories, additional_categories = _mr_build_categories(sc, config, auth)

        donation_urls = [
            {'id': pid, 'platform': platform, 'url': donation[key]}
            for key, (pid, platform) in self._MR_DONATION_PLATFORMS.items()
            if donation.get(key)
        ]

        mr_type = _MR_TYPE_MAP.get(config.get('type', 'pack'), 'resourcepack')
        body: dict = {
            'title': sc.get('name', ''),
            'description': sc.get('summary', ''),
            'body': description,
            'categories': categories,
            'additional_categories': additional_categories,
            'issues_url': links.get('issues') or None,
            'source_url': links.get('source') or None,
            'wiki_url': links.get('wiki') or None,
            'discord_url': sc.get('discord') or None,
            'donation_urls': donation_urls,
            'requested_status': 'approved',
        }
        if mr_type == 'mod':
            body['client_side'] = config.get('client_side', 'required')
            body['server_side'] = config.get('server_side', 'unsupported')
        license_id = config.get('license')
        if license_id:
            body['license_id'] = license_id

        _mr_patch_json(f'{_MR_API}/project/{project_id}', auth, body)

    def img_tag(self, url: str, name: str) -> str:
        return f'<img src="{url}" width="600" alt="{name}"><br><br>'

    def upload_images(self, project_id: str, auth: dict, image_list: list, images_dir: Path, verbosity: int) -> dict[str, str]:
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
                'featured': img_entry.get('featured', False),
                'description': img_entry.get('description', ''),
            })
        if verbosity >= 1:
            print(f'  [Modrinth] syncing gallery ({len(images)} images)')
        self.sync_gallery(project_id, auth, images)
        project = _mr_get(f'{_MR_API}/project/{project_id}', auth) or {}
        gallery = project.get('gallery') or []
        return {
            Path(item['title']).stem: item.get('url', '')
            for item in gallery
            if item.get('title') and item.get('url')
        }

    def push(
        self,
        *,
        project_id: str,
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
            **config.get('modrinth', {}),
        }

        if verbosity >= 1:
            print('  [Modrinth] uploading icon')
        icon_bytes = prepare_icon(icon_path, verbosity=verbosity)
        self.upload_icon(project_id, auth, icon_bytes)

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
                print(f'  [Modrinth] syncing gallery ({len(images)} images)')
            self.sync_gallery(project_id, auth, images)

        if verbosity >= 1:
            print('  [Modrinth] updating project')
        self.update_project(project_id, auth, sc, description, config)

    def pull(
        self,
        project_id: str,
        auth: dict,
        puppy_dir: Path,
        images: bool = True,
        verbosity: int = 0,
    ) -> dict:
        if verbosity >= 1:
            print('  [Modrinth] fetching project')
        data = _mr_get(f'{_MR_API}/project/{project_id}', auth)
        if not data or not isinstance(data, dict):
            raise SystemExit(f'Could not fetch Modrinth project: {project_id}')

        gallery = data.get('gallery') or []

        site_dir = puppy_dir / 'modrinth'
        site_dir.mkdir(parents=True, exist_ok=True)
        body = data.get('body', '')
        if body:
            (site_dir / 'description.md').write_text(body)

        image_entries = []
        for item in gallery:
            if not item.get('title'):
                continue
            entry = {'file': item['title'], 'description': item.get('description', '')}
            if item.get('featured'):
                entry['featured'] = True
            image_entries.append(entry)

        if images:
            icon_url = data.get('icon_url')
            if icon_url:
                existing = [
                    p for p in puppy_dir.iterdir()
                    if p.suffix in ('.png', '.jpg', '.jpeg')
                    and p.name not in ('banner.png', 'logo.png')
                ]
                if not existing:
                    if verbosity >= 1:
                        print('  [Modrinth] downloading icon')
                    _mr_download(icon_url, puppy_dir / 'pack.png')

            if gallery:
                images_dir = puppy_dir / 'images'
                images_dir.mkdir(parents=True, exist_ok=True)
                if verbosity >= 1:
                    print(f'  [Modrinth] downloading {len(gallery)} gallery images')
                for item in gallery:
                    url = item.get('url', '')
                    title = item.get('title', '')
                    if url and title:
                        stem = Path(title).stem.strip('_')
                        suffix = Path(url.split('?')[0]).suffix or '.jpg'
                        _mr_download(url, images_dir / (stem + suffix))

        license_id = (data.get('license') or {}).get('id') or None

        links = {
            k: v for k, v in (
                ('issues', data.get('issues_url')),
                ('source', data.get('source_url')),
                ('wiki', data.get('wiki_url')),
            ) if v
        }

        socials = {}
        if data.get('discord_url'):
            socials['discord'] = data['discord_url']

        donation = {
            key: entry['url']
            for entry in (data.get('donation_urls') or [])
            for key in (_MR_DONATION_ID_TO_KEY.get(entry.get('id', '')),)
            if key and entry.get('url')
        }

        all_cats = (data.get('categories') or []) + (data.get('additional_categories') or [])
        resolution = [cat for cat in all_cats if cat in _MR_RESOLUTION_TIERS]
        category = [cat for cat in all_cats if cat not in _MR_RESOLUTION_TIERS]

        return {
            'config': {
                'name': data.get('title', ''),
                'summary': data.get('description', ''),
                'links': links or None,
                'socials': socials or None,
                'images': image_entries,
            },
            'modrinth': {
                'id': data['id'],
                'slug': data['slug'],
                'license': license_id,
                'donation': donation or None,
                'resolution': resolution if resolution else None,
                'category': category if category else None,
            },
        }

    def apply_settings(self, settings: dict, sc: dict) -> None:
        mr = settings.setdefault('modrinth', {})
        mr['discord'] = sc.get('discord')
        donation = sc.get('donation') or {}
        mr['donation'] = {k: donation.get(k) for k in self._DONATION_KEYS}

    def auth_yaml_entry(self) -> str:
        return 'modrinth:\n  token: YOUR_MODRINTH_TOKEN\n'

    def init_template(self) -> tuple[str, str]:
        return ('description.md', '<!-- Modrinth description (Markdown) -->\n')

    def url_for(self, site_config: dict) -> str | None:
        ref = site_config.get('slug') or site_config.get('id')
        if not ref:
            return None
        mr_type = _MR_TYPE_MAP.get(site_config.get('type', 'pack'), 'resourcepack')
        return f'https://modrinth.com/{mr_type}/{ref}'
