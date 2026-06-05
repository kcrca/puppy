from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

from puppy.sites.base import Site


# Maps SPDX license IDs to the keys PU's modrinth.js license map uses
_SPDX_TO_PU_MR = {
    'CC0-1.0': 'CC Zero (Public Domain equivalent)',
    'CC-BY-4.0': 'CC-BY 4.0',
    'CC-BY-SA-4.0': 'CC-BY-SA 4.0',
    'CC-BY-NC-4.0': 'CC-BY-NC 4.0',
    'CC-BY-NC-SA-4.0': 'CC-BY-NC-SA 4.0',
    'CC-BY-ND-4.0': 'CC-BY-ND 4.0',
    'CC-BY-NC-ND-4.0': 'CC-BY-NC-ND 4.0',
    'MIT': 'MIT License',
    'Apache-2.0': 'Apache License 2.0',
    'GPL-2.0': 'GNU General Public License v2',
    'GPL-3.0': 'GNU General Public License v3',
    'LGPL-2.1': 'GNU Lesser General Public License v2.1',
    'LGPL-3.0': 'GNU Lesser General Public License v3',
    'AGPL-3.0': 'GNU Affero General Public License v3',
    'MPL-2.0': 'Mozilla Public License 2.0',
    'BSD-2-Clause': 'BSD 2-Clause "Simplified" License',
    'BSD-3-Clause': 'BSD 3-Clause "New" or "Revised" License',
    'ISC': 'ISC License',
    'Zlib': 'zlib License',
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
            res = str(resolution)
            tags = config.setdefault('modrinth', {}).setdefault('tags', {})
            for tier in ['8x-', '16x', '32x', '48x', '64x', '128x', '256x', '512x+']:
                tags.setdefault(tier, tier == f'{res}x')

        license_ = config.get('license')
        if license_:
            pu_license = _SPDX_TO_PU_MR.get(license_, license_)
            config.setdefault('modrinth', {}).setdefault('license', pu_license)

        links = config.get('links') or {}
        if isinstance(links, dict):
            donation = {
                mr_key: links[link_key]
                for link_key, mr_key in self._LINKS_TO_MR_DONATION.items()
                if links.get(link_key)
            }
            if donation:
                config.setdefault('modrinth', {}).setdefault('donation', donation)

    def preview_rows(self, sc: dict) -> list[tuple[str, str]]:
        rows = []
        active_tags = [k for k, v in sc.get('tags', {}).items() if v]
        if active_tags:
            rows.append(('Tags', ', '.join(active_tags)))
        if sc.get('license'):
            rows.append(('License', str(sc['license'])))
        return rows

    def needs_upload(self, site_id, auth: dict, zip_path: Path, version: str, project) -> bool:
        local_hash = hashlib.sha512(zip_path.read_bytes()).hexdigest()
        headers = {'User-Agent': 'puppy/1.0'}
        token = auth.get('modrinth')
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

    def resolve_id(self, config: dict, auth: dict, verbosity: int) -> dict:
        mr = config.get('modrinth', {})
        if mr.get('id') or not mr.get('slug'):
            return config
        slug = mr['slug']
        try:
            headers = {'User-Agent': 'puppy/1.0'}
            token = auth.get('modrinth')
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

    def apply_settings(self, settings: dict, sc: dict) -> None:
        mr = settings.setdefault('modrinth', {})
        mr['discord'] = sc.get('discord')
        donation = sc.get('donation') or {}
        mr['donation'] = {k: donation.get(k) for k in self._DONATION_KEYS}

    def auth_yaml_entry(self) -> str:
        return 'modrinth: YOUR_MODRINTH_TOKEN\n'

    def init_template(self) -> tuple[str, str]:
        return ('description.md', '<!-- Modrinth description (Markdown) -->\n')

    def url_for(self, site_config: dict) -> str | None:
        ref = site_config.get('slug') or site_config.get('id')
        if not ref:
            return None
        site_type = site_config.get('type', 'resourcepack')
        return f'https://modrinth.com/{site_type}/{ref}'
