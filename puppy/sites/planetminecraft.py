from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

from puppy.errors import AuthExpiredError
from puppy.images import find_image, prepare_gallery_image
from puppy.renderer import md_to_bbcode
from puppy.sites.base import Site


_PMC_BASE = 'https://www.planetminecraft.com'
_PMC_MANAGE = '/account/manage/texture-packs/'
_PMC_AJAX = f'{_PMC_BASE}/ajax.php'

_PMC_RESOLUTIONS = {
    8: 6, 16: 1, 32: 2, 64: 3, 128: 4, 256: 5, 512: 7, 1024: 8, 2048: 9, 4096: 10,
}

_PMC_CATEGORIES = {
    'Experimental': 26, 'PvP': 154, 'Realistic': 25, 'Simplistic': 23,
    'Themed': 24, 'Unreleased': 86, 'Other': 27,
}

_PMC_MODIFIES = {
    'armor': 37, 'art': 35, 'environment': 30, 'font': 31, 'gui': 34,
    'items': 33, 'misc': 38, 'mobs': 36, 'particles': 41, 'terrain': 32,
    'audio': 152, 'models': 153,
}


def _pmc_headers(cookie: str, csrf: str = '', referrer: str = '') -> dict:
    h = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Origin': _PMC_BASE,
    }
    if csrf:
        h['x-pmc-csrf-token'] = csrf
    if referrer:
        h['Referer'] = referrer
    return h


def _pmc_get_page(project_id, cookie: str) -> tuple[BeautifulSoup, str]:
    url = f'{_PMC_BASE}{_PMC_MANAGE}{project_id}/'
    req = urllib.request.Request(url, headers=_pmc_headers(cookie))
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode('utf-8', errors='replace')
    soup = BeautifulSoup(html, 'html.parser')
    tag = soup.find(id='core-csrf-token')
    if not tag or not tag.get('content'):
        raise AuthExpiredError(401, 'PMC CSRF token not found — auth may have expired')
    return soup, tag['content']


def _pmc_url_to_filename(url: str) -> str:
    stem = url.split('?')[0].rsplit('/', 1)[-1].rsplit('.', 1)[0]
    if stem.endswith(('_s', '_l')):
        stem = stem[:-2]
    if '-' in stem:
        prefix, rest = stem.split('-', 1)
        if prefix.isdigit():
            stem = rest
    return stem.replace('-', '_')


def _pmc_scrape_hidden(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find('input', {'name': name})
    return tag['value'] if tag else ''


def _pmc_select_value(soup: BeautifulSoup, select_id: str) -> str:
    sel = soup.find('select', id=select_id)
    if not sel:
        return ''
    opt = sel.find('option', selected=True)
    return opt['value'] if opt else ''


def _pmc_tag_ids(soup: BeautifulSoup) -> list[str]:
    return [tag['data-tag-id'] for tag in soup.find_all(attrs={'data-tag-id': True})]


def _pmc_existing_images(soup: BeautifulSoup) -> list[dict]:
    images = []
    for tag in soup.find_all(attrs={'data-media-item-id': True}):
        images.append({
            'id': tag['data-media-item-id'],
            'caption': tag.get('data-caption', ''),
        })
    return images


def _pmc_download(url: str, dest: Path, cookie: str) -> None:
    if not url.startswith('http'):
        url = f'{_PMC_BASE}{url}'
    req = urllib.request.Request(url, headers=_pmc_headers(cookie))
    with urllib.request.urlopen(req, timeout=30) as r:
        dest.write_bytes(r.read())


def _pmc_multipart(fields: list[tuple], files: list[tuple] = None) -> tuple[bytes, bytes]:
    boundary = b'----PuppyPMCBoundary'
    parts = []
    for name, value in fields:
        parts.append(
            f'--{boundary.decode()}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    for field_name, filename, data, mime_type in (files or []):
        parts.append(
            f'--{boundary.decode()}\r\nContent-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\nContent-Type: {mime_type}\r\n\r\n'.encode()
            + data + b'\r\n'
        )
    parts.append(f'--{boundary.decode()}--\r\n'.encode())
    return b''.join(parts), boundary


def _pmc_post(project_id, cookie: str, csrf: str, fields: list[tuple], files: list[tuple] = None) -> dict:
    referrer = f'{_PMC_BASE}{_PMC_MANAGE}{project_id}/'
    body, boundary = _pmc_multipart(fields, files)
    req = urllib.request.Request(
        _PMC_AJAX,
        data=body,
        headers={
            **_pmc_headers(cookie, csrf=csrf, referrer=referrer),
            'Content-Type': f'multipart/form-data; boundary={boundary.decode()}',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise AuthExpiredError(e.code, e.read().decode(errors='replace'))
        raise


def _pmc_sync_gallery(
    project_id, cookie: str, csrf: str, soup: BeautifulSoup,
    image_list: list, images_dir: Path, verbosity: int,
) -> None:
    existing = _pmc_existing_images(soup)
    special = {'Project Thumbnail', 'Project Logo'}
    existing_by_title = {
        item['caption'].split(' - ')[0]: item['id']
        for item in existing
        if item['caption'].split(' - ')[0] not in special
    }
    desired_titles = {img['file'] for img in image_list}

    for title, media_id in existing_by_title.items():
        if title not in desired_titles:
            _pmc_post(project_id, cookie, csrf, [
                ('module', 'tools/media'), ('myaction', 'delete'), ('modern', 'true'),
                ('media_id', media_id), ('media_key', 'image_key'),
                ('connect_id', str(project_id)),
            ])
            if verbosity >= 1:
                print(f'    deleted PMC gallery image: {title}')

    for img in image_list:
        title = img.get('file', '')
        if title in existing_by_title:
            continue
        src = find_image(img['file'], images_dir)
        data = prepare_gallery_image(src, verbosity=verbosity)
        r = _pmc_post(project_id, cookie, csrf, [
            ('module', 'tools/media'), ('myaction', 'create'), ('modern', 'true'),
            ('media_id', 'new'), ('media_key', 'image_key'),
            ('connect_id', str(project_id)),
        ])
        media_id = r.get('media_id')
        if not media_id:
            raise SystemExit(f'PMC: failed to create image slot for {img["file"]}: {r}')
        caption = f'{title} - {img["description"]}' if img.get('description') else title
        r2 = _pmc_post(project_id, cookie, csrf, [
            ('module', 'tools/media'), ('myaction', 'save'), ('modern', 'true'),
            ('media_id', str(media_id)), ('media_key', 'image_key'),
            ('connect_id', str(project_id)), ('title', caption),
        ], files=[('filename', f'{title}.jpg', data, 'image/jpeg')])
        if r2.get('status') != 'success':
            raise SystemExit(f'PMC: failed to upload image {img["file"]}: {r2}')
        if verbosity >= 1:
            print(f'    uploaded PMC gallery image: {title}')


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
    ) -> None:
        cookie = auth.get('planetminecraft', '')
        sc = config.get('planetminecraft', {})

        if verbosity >= 1:
            print('  [PlanetMinecraft] fetching project page')
        soup, csrf = _pmc_get_page(project_id, cookie)

        hidden_names = ('member_id', 'subject_id', 'group', 'module', 'module_task')
        hidden = {name: _pmc_scrape_hidden(soup, name) for name in hidden_names}
        current_op1 = _pmc_select_value(soup, 'op1')
        tag_ids = _pmc_tag_ids(soup)

        if image_list:
            if verbosity >= 1:
                print(f'  [PlanetMinecraft] syncing gallery ({len(image_list)} images)')
            _pmc_sync_gallery(project_id, cookie, csrf, soup, image_list, images_dir, verbosity)

        category = _PMC_CATEGORIES.get(sc.get('category', ''), 27)
        resolution = _PMC_RESOLUTIONS.get(int(sc.get('resolution', 16)), 1)

        mr = config.get('modrinth', {})
        cf = config.get('curseforge', {})
        mr_slug = mr.get('slug') or mr.get('id')
        cf_slug = cf.get('slug')
        if mr_slug:
            download_url = f'https://modrinth.com/resourcepack/{mr_slug}'
        elif cf_slug:
            download_url = f'https://www.curseforge.com/minecraft/texture-packs/{cf_slug}'
        else:
            download_url = ''

        website = sc.get('website') or {}

        fields = [
            ('member_id', hidden['member_id']),
            ('resource_id', str(project_id)),
            ('subject_id', hidden['subject_id']),
            ('group', hidden['group']),
            ('module', hidden['module']),
            ('module_task', hidden['module_task']),
            ('server_id', ''),
            ('title', config.get('name', '')),
            ('op0', str(resolution)),
            ('progress', str(sc.get('progress', 100))),
            ('description', description),
            ('wid1', '1'),
            ('wfile1', '1'),
            ('wurl1', download_url),
            ('wtitle1', 'Download here'),
            ('wid0', '0'),
            ('wfile0', '0'),
            ('wurl0', website.get('link', '')),
            ('wtitle0', website.get('title', '')),
            ('credit', sc.get('credit', '')),
            ('item_tag', ''),
            ('tag_ids', ','.join(tag_ids)),
            ('allowcomments', '1'),
            ('saved_data', ''),
            ('live', '1'),
            ('folder_id[]', str(category)),
        ]

        if current_op1:
            fields.append(('op1', current_op1))

        video = sc.get('video') or config.get('video')
        if video:
            fields.append(('youtube', video))

        modifies = sc.get('modifies') or {}
        for mod, on in modifies.items():
            if on and mod in _PMC_MODIFIES:
                fields.append(('folder_id[]', str(_PMC_MODIFIES[mod])))

        if verbosity >= 1:
            print('  [PlanetMinecraft] updating details')
        result = _pmc_post(project_id, cookie, csrf, fields)
        if result.get('status') != 'success':
            raise SystemExit(f'PMC update failed: {result}')

    def pull(
        self,
        project_id,
        auth: dict,
        puppy_dir: Path,
        images: bool = True,
        verbosity: int = 0,
    ) -> dict:
        cookie = auth.get('planetminecraft', '')

        if verbosity >= 1:
            print('  [PlanetMinecraft] fetching project page')
        soup, _ = _pmc_get_page(project_id, cookie)

        _CATEGORIES_INV = {v: k for k, v in _PMC_CATEGORIES.items()}
        _RESOLUTIONS_INV = {v: k for k, v in _PMC_RESOLUTIONS.items()}

        cat_sel = soup.find(attrs={'id': 'folder_id[]'})
        cat_opt = cat_sel.find('option', selected=True) if cat_sel else None
        category = _CATEGORIES_INV.get(int(cat_opt['value']), 'Other') if cat_opt else 'Other'

        res_sel = soup.find('select', id='op0')
        res_opt = res_sel.find('option', selected=True) if res_sel else None
        resolution = _RESOLUTIONS_INV.get(int(res_opt['value']), 16) if res_opt else 16

        progress_tag = soup.find(id='progress')
        progress = int(progress_tag['value']) if progress_tag and progress_tag.get('value') else 100

        credit_tag = soup.find('input', {'name': 'credit'})
        credit = credit_tag['value'] if credit_tag else ''

        modifies = {}
        mod_container = soup.find(id='main_folder_modified')
        if mod_container:
            for item in mod_container.find_all(class_='folder-item'):
                inp = item.find('input')
                lbl = item.find('label')
                if inp and lbl:
                    key = lbl.get_text(strip=True).lower()
                    modifies[key] = inp.has_attr('checked')

        tags = []
        tags_container = soup.find(id='item_tags')
        if tags_container:
            for tag in tags_container.find_all(class_='tag'):
                text = tag.get_text(strip=True)
                if text:
                    tags.append(text)

        name_tag = soup.find('input', {'name': 'title'})
        name = name_tag['value'] if name_tag else ''

        video_tag = soup.find('input', {'name': 'youtube'})
        video = video_tag['value'] if video_tag and video_tag.get('value') else ''

        image_items = []
        for thumb in soup.select('.image_list > .thumbnail'):
            url = thumb.get('data-full-filename', '')
            caption = thumb.get('data-caption', '')
            if not url:
                continue
            if caption == 'Project Thumbnail':
                if images:
                    dest = puppy_dir / 'banner.png'
                    if not dest.exists():
                        try:
                            _pmc_download(url, dest, cookie)
                        except Exception:
                            if verbosity >= 1:
                                print('    failed to download banner')
                continue
            if caption == 'Project Logo':
                if images:
                    dest = puppy_dir / 'logo.png'
                    if not dest.exists():
                        try:
                            _pmc_download(url, dest, cookie)
                        except Exception:
                            if verbosity >= 1:
                                print('    failed to download logo')
                continue
            parts = caption.split(' - ', 1)
            description = parts[1] if len(parts) > 1 else ''
            file = _pmc_url_to_filename(url)
            image_items.append({'url': url, 'file': file, 'description': description})

        if images and image_items:
            images_dir = puppy_dir / 'images'
            images_dir.mkdir(parents=True, exist_ok=True)
            if verbosity >= 1:
                print(f'  [PlanetMinecraft] downloading {len(image_items)} gallery images')
            for item in image_items:
                dest = images_dir / f'{item["file"]}.png'
                try:
                    _pmc_download(item['url'], dest, cookie)
                except Exception:
                    if verbosity >= 1:
                        print(f'    failed to download: {item["file"]}')

        image_entries = [{'file': item['file'], 'description': item['description']} for item in image_items]

        pmc_result: dict = {'id': project_id}
        if category:
            pmc_result['category'] = category
        if resolution:
            pmc_result['resolution'] = resolution
        pmc_result['progress'] = progress
        if credit:
            pmc_result['credit'] = credit
        if modifies:
            pmc_result['modifies'] = modifies
        if tags:
            pmc_result['tags'] = tags

        config_result: dict = {'images': image_entries}
        if name:
            config_result['name'] = name
        if video:
            config_result['video'] = video

        return {
            'config': config_result,
            'planetminecraft': pmc_result,
        }

    def submit_log(self, project_id, auth: dict, version: str, config: dict) -> None:
        cookie = auth.get('planetminecraft', '')
        soup, csrf = _pmc_get_page(project_id, cookie)
        member_id = _pmc_scrape_hidden(soup, 'member_id')
        changelog = config.get('changelog', '')
        fields = [
            ('log_title', f'Update v{version}'),
            ('content', changelog),
            ('module', 'public/resource/manage'),
            ('module_plugin', 'log'),
            ('module_plugin_task', 'create'),
            ('submit_log', 'SAVE LOG'),
            ('member_id', member_id),
            ('resource_id', str(project_id)),
        ]
        result = _pmc_post(project_id, cookie, csrf, fields)
        if result.get('status') != 'success':
            feedback = result.get('feedback', '')
            if 'daily update limit' in feedback:
                raise SystemExit('PMC: daily update limit reached — try again tomorrow')
            raise SystemExit(f'PMC: failed to submit version log: {result}')
