from __future__ import annotations

from pathlib import Path

import yaml

from puppy.renderer import md_to_bbcode
from puppy.sites.base import Site


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
