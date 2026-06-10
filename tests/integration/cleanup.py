"""Delete all projects from test-account on CF, MR, and/or PMC.

Usage:
    python tests/integration/cleanup.py            # all sites
    python tests/integration/cleanup.py --site mr
    python tests/integration/cleanup.py --site cf
    python tests/integration/cleanup.py --site pmc
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

_INTEGRATION_DIR = Path(__file__).parent
_AUTH_FILE = _INTEGRATION_DIR / 'puppy' / 'auth.yaml'

_PMC_BASE = 'https://www.planetminecraft.com'
_MR_API = 'https://api.modrinth.com/v2'
_MR_UA = 'puppy-test/1.0'
_CF_DASH = 'https://authors.curseforge.com/_api'
_CF_API = 'https://api.curseforge.com/v1'
_CF_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'


def _load_auth() -> dict:
    if not _AUTH_FILE.exists():
        return {}
    return yaml.safe_load(_AUTH_FILE.read_text()) or {}


def _mr_request(path: str, token: str, method: str = 'GET') -> object:
    req = urllib.request.Request(
        f'{_MR_API}{path}',
        method=method,
        headers={'Authorization': token, 'User-Agent': _MR_UA},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()) if method == 'GET' else None


def _cf_fetch(url: str, cookie: str) -> object:
    req = urllib.request.Request(url, headers={
        'User-Agent': _CF_UA,
        'Cookie': cookie,
        'Origin': 'https://authors.curseforge.com',
        'Referer': 'https://authors.curseforge.com/',
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _cf_delete_project(project_id: int, cookie: str) -> None:
    req = urllib.request.Request(
        f'{_CF_DASH}/projects/{project_id}',
        method='DELETE',
        headers={
            'User-Agent': _CF_UA,
            'Cookie': cookie,
            'Origin': 'https://authors.curseforge.com',
            'Referer': 'https://authors.curseforge.com/',
        },
    )
    with urllib.request.urlopen(req) as _:
        pass


def _pmc_list_projects(page) -> list[tuple[int, str]]:
    import re
    projects = []
    for path in ('/account/manage/texture-packs/', '/account/manage/projects/'):
        page.goto(f'{_PMC_BASE}{path}', wait_until='networkidle')
        soup = BeautifulSoup(page.content(), 'html.parser')
        for a in soup.find_all('a', href=re.compile(rf'{re.escape(path)}\d+/')):
            m = re.search(r'/(\d+)/', a['href'])
            if m:
                projects.append((int(m.group(1)), path))
    seen = set()
    return [(pid, path) for pid, path in projects if not (pid in seen or seen.add(pid))]


def _mr_cleanup(token: str, username: str) -> None:
    projects = _mr_request(f'/user/{username}/projects', token)
    for p in projects:
        print(f'[cleanup] Deleting Modrinth: {p["slug"]}')
        _mr_request(f'/project/{p["id"]}', token, method='DELETE')


def _cf_cleanup(cookie: str) -> None:
    all_projects: list = []
    start = 0
    while True:
        params = urllib.parse.urlencode({'filter': '{}', 'range': f'[{start},{start + 99}]', 'sort': '["id","ASC"]'})
        try:
            data = _cf_fetch(f'{_CF_DASH}/projects?{params}', cookie)
        except Exception:
            break
        if not isinstance(data, list) or not data:
            break
        all_projects.extend(data)
        if len(data) < 100:
            break
        start += 100
    for p in all_projects:
        label = p.get('slug') or p['id']
        print(f'[cleanup] Deleting CurseForge: {label}')
        try:
            _cf_delete_project(p['id'], cookie)
        except Exception as e:
            print(f'[cleanup] Warning: failed to delete {label}: {e}')


def _pmc_cleanup(cookie: str) -> None:
    from playwright.sync_api import sync_playwright
    c_name, _, c_value = cookie.partition('=')

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        ctx = browser.new_context()
        ctx.add_cookies([{
            'name': c_name.strip(), 'value': c_value.strip(),
            'domain': 'www.planetminecraft.com', 'path': '/',
        }])
        page = ctx.new_page()

        for project_id, manage_path in _pmc_list_projects(page):
            print(f'[cleanup] Deleting PMC project: {project_id}')
            try:
                page.goto(f'{_PMC_BASE}{manage_path}{project_id}/', wait_until='networkidle')
                page.click('.delete_submission')
                page.wait_for_timeout(500)
                confirm = page.query_selector('.pmc_dialog .site_btn')
                if confirm:
                    confirm.click()
                    page.wait_for_timeout(1000)
            except Exception as e:
                print(f'[cleanup] Warning: failed to delete PMC {project_id}: {e}')

        page.wait_for_timeout(3000)
        remaining = [pid for pid, _ in _pmc_list_projects(page)]
        browser.close()

    if remaining:
        print(f'[cleanup] Warning: PMC cleanup incomplete — {len(remaining)} project(s) still present: {remaining}')


def run_cleanup(auth: dict, sites: set[str] | None = None) -> None:
    if sites is None:
        sites = {'mr', 'cf', 'pmc'}

    if 'mr' in sites:
        mr = auth.get('modrinth', {})
        token = mr.get('token')
        username = mr.get('username')
        if token and username:
            _mr_cleanup(token, username)
        elif token:
            print('[cleanup] Skipping Modrinth: add modrinth.username to auth.yaml')

    if 'cf' in sites:
        cf_cookie = auth.get('curseforge', {}).get('cookie')
        if cf_cookie:
            _cf_cleanup(cf_cookie)

    if 'pmc' in sites:
        pmc_cookie = auth.get('planetminecraft', {}).get('cookie')
        if pmc_cookie:
            _pmc_cleanup(pmc_cookie)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Delete all projects from test accounts.')
    parser.add_argument('--site', choices=['mr', 'cf', 'pmc'], help='Limit to one site (default: all)')
    args = parser.parse_args()
    run_cleanup(_load_auth(), sites={args.site} if args.site else None)
