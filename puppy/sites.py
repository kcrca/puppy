from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from puppy.renderer import md_to_bbcode, md_to_html


class Site:
    name: str
    aliases: list[str]
    label: str
    template_ext: str
    desc_exts: list[str]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'Site({self.name!r})'

    def convert_md(self, text: str) -> str:
        return text

    def shield_tags(self, tags: list[str]) -> tuple[dict, dict]:
        return {}, {}

    def apply_neutral(self, config: dict) -> None:
        pass

    def preview_rows(self, sc: dict) -> list[tuple[str, str]]:
        return []

    def needs_upload(self, site_id, auth: dict, zip_path: Path, version: str, project) -> bool:
        return True

    def resolve_id(self, config: dict, auth: dict, verbosity: int) -> dict:
        return config

    def post_upload(self, puppy_dir: Path, version: str) -> None:
        pass

    def apply_settings(self, settings: dict, sc: dict) -> None:
        pass

    def auth_yaml_entry(self) -> str:
        return ''

    def puppy_yaml_entry(self, pack: str) -> str:
        return f'{self.name}:\n  id: null\n  slug: {pack}\n'

    def init_template(self) -> tuple[str, str]:
        raise NotImplementedError

    def url_for(self, site_config: dict) -> str | None:
        raise NotImplementedError


class CurseForgeSite(Site):
    name = 'curseforge'
    aliases = ['cf']
    label = 'CurseForge'
    template_ext = '.html'
    desc_exts = ['.html', '.md']

    def convert_md(self, text: str) -> str:
        return md_to_html(text)

    def apply_neutral(self, config: dict) -> None:
        resolution = config.get('resolution')
        if resolution is not None:
            config.setdefault('curseforge', {}).setdefault('mainCategory', f'{resolution}x')

        license_ = config.get('license')
        if license_:
            cf_license = ' '.join(license_.rsplit('-', 1)) if '-' in license_ else license_
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
            headers={
                'cookie': cf_auth.get('cookie', ''),
                'Content-Type': 'application/json',
            },
        )
        with urllib.request.urlopen(req) as r:
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
        with urllib.request.urlopen(req) as r:
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
            with urllib.request.urlopen(req) as r:
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


class PlanetMinecraftSite(Site):
    name = 'planetminecraft'
    aliases = ['pmc']
    label = 'PlanetMinecraft'
    template_ext = '.bbcode'
    desc_exts = ['.bbcode', '.md']

    def convert_md(self, text: str) -> str:
        return md_to_bbcode(text)

    def shield_tags(self, tags: list[str]) -> tuple[dict, dict]:
        return {t: f'[{t}]' for t in tags}, {t: f'[/{t}]' for t in tags}

    def apply_neutral(self, config: dict) -> None:
        resolution = config.get('resolution')
        if resolution is not None:
            res = str(resolution)
            pmc = config.setdefault('planetminecraft', {})
            pmc.setdefault('resolution', int(resolution))
            pmc_tags = pmc.setdefault('tags', [])
            for res_tag in [f'{res}x', f'{res}x{res}']:
                if res_tag not in pmc_tags:
                    pmc_tags.append(res_tag)

        progress = config.get('progress')
        if progress is not None:
            config.setdefault('planetminecraft', {}).setdefault('progress', int(progress))

        links = config.get('links') or {}
        if isinstance(links, dict) and links.get('home'):
            config.setdefault('planetminecraft', {}).setdefault('website', {}).setdefault('link', links['home'])

    def preview_rows(self, sc: dict) -> list[tuple[str, str]]:
        rows = []
        if sc.get('category'):
            rows.append(('Category', str(sc['category'])))
        if sc.get('resolution'):
            rows.append(('Resolution', f'{sc["resolution"]}x'))
        if sc.get('progress') is not None:
            rows.append(('Progress', f'{sc["progress"]}%'))
        active_mods = [k for k, v in sc.get('modifies', {}).items() if v]
        if active_mods:
            rows.append(('Modifies', ', '.join(active_mods)))
        pmc_tags = sc.get('tags', [])
        if pmc_tags:
            rows.append(('Tags', ', '.join(str(t) for t in pmc_tags)))
        if sc.get('credit'):
            rows.append(('Credit', str(sc['credit'])))
        return rows

    def needs_upload(self, site_id, auth: dict, zip_path: Path, version: str, project) -> bool:
        state_path = project.puppy_dir / '.publish_state.yaml'
        if not state_path.exists():
            return True
        state = yaml.safe_load(state_path.read_text()) or {}
        return state.get(self.name, {}).get('version') != str(version)

    def post_upload(self, puppy_dir: Path, version: str) -> None:
        state_path = puppy_dir / '.publish_state.yaml'
        state = yaml.safe_load(state_path.read_text()) if state_path.exists() else {}
        state = state or {}
        state.setdefault(self.name, {})['version'] = str(version)
        state_path.write_text(yaml.dump(state, default_flow_style=False))

    def apply_settings(self, settings: dict, sc: dict) -> None:
        pmc = settings.setdefault('planetminecraft', {})
        website = sc.get('website') or {}
        pmc['website'] = {'link': website.get('link'), 'title': website.get('title')}

    def auth_yaml_entry(self) -> str:
        return 'planetminecraft: pmc_autologin=YOUR_PMC_AUTOLOGIN_COOKIE\n'

    def init_template(self) -> tuple[str, str]:
        return ('description.bbcode', '[b]Planet Minecraft description (BBCode)[/b]\n')

    def url_for(self, site_config: dict) -> str | None:
        ref = site_config.get('slug') or site_config.get('id')
        if not ref:
            return None
        return f'https://www.planetminecraft.com/texture-pack/{ref}/'


CURSEFORGE = CurseForgeSite()
MODRINTH = ModrinthSite()
PMC = PlanetMinecraftSite()

SITES: list[Site] = [CURSEFORGE, MODRINTH, PMC]
SITE_MAP: dict[str, Site] = {s.name: s for s in SITES}
_ALIASES: dict[str, str] = {a: s.name for s in SITES for a in s.aliases}


class SiteVisitor:
    """Iterates over the active sites, respecting an optional filter.

    Construct with the value of the -s/--site CLI flag (or None for all sites).
    """

    def __init__(self, filter: str = None):
        if filter:
            requested = [_ALIASES.get(s.strip(), s.strip()) for s in filter.split(',')]
            unknown = [s for s in requested if s not in SITE_MAP]
            if unknown:
                raise SystemExit(
                    f'Unknown site(s): {", ".join(unknown)}. Valid: {", ".join(SITE_MAP)}'
                )
            self.sites = [s for s in SITES if s.name in requested]
        else:
            self.sites = list(SITES)

    def __iter__(self):
        return iter(self.sites)

    def __contains__(self, site) -> bool:
        return site in self.sites

    def id_or_skip(self, site, value) -> object:
        """Return value for active sites, None for inactive ones."""
        return value if site in self.sites else None
