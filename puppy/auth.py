"""Cookie harvesting for puppy auth command."""
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

from puppy.core import find_puppy_home

_CF_URL = 'https://authors.curseforge.com'
_PMC_URL = 'https://www.planetminecraft.com'

_COOKIE_SITES = {'curseforge', 'planetminecraft'}
_TOKEN_SITES = {'curseforge', 'modrinth'}
_ALL_SITES = {'curseforge', 'modrinth', 'planetminecraft'}
_ALIASES = {'cf': 'curseforge', 'mr': 'modrinth', 'pmc': 'planetminecraft'}


def _resolve_sites(site: str | None, puppy_home: Path | None = None) -> list[str]:
    if not site:
        if puppy_home:
            puppy_yaml = puppy_home / 'puppy.yaml'
            if puppy_yaml.exists():
                config = yaml.safe_load(puppy_yaml.read_text()) or {}
                declared = config.get('sites')
                if declared:
                    result = []
                    for s in declared:
                        canonical = _ALIASES.get(str(s).strip(), str(s).strip())
                        if canonical not in _ALL_SITES:
                            raise SystemExit(f'Unknown site in sites: {s!r}. Choose from: cf, mr, pmc')
                        result.append(canonical)
                    return result
        return list(_ALL_SITES)
    result = []
    for s in site.split(','):
        s = s.strip()
        canonical = _ALIASES.get(s, s)
        if canonical not in _ALL_SITES:
            raise SystemExit(f'Unknown site: {s!r}. Choose from: cf, mr, pmc')
        result.append(canonical)
    return result


def _firefox_profile_dirs() -> list[Path]:
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'Firefox' / 'Profiles'
    elif sys.platform == 'win32':
        base = Path.home() / 'AppData' / 'Roaming' / 'Mozilla' / 'Firefox' / 'Profiles'
    else:
        base = Path.home() / '.mozilla' / 'firefox'
    if not base.exists():
        return []
    profiles = [p.parent for p in base.glob('*/cookies.sqlite')]
    return sorted(profiles, key=lambda p: p.stat().st_mtime, reverse=True)


def _open_context(p):
    exe = p.firefox.executable_path
    if not Path(exe).exists():
        raise SystemExit('Firefox not installed for Playwright. Run: playwright install firefox')
    profiles = _firefox_profile_dirs()
    if not profiles:
        raise SystemExit(
            'No Firefox profile found. Install Firefox, log into the required sites, '
            'quit Firefox, then re-run puppy auth.'
        )
    profile_dir = profiles[0]
    print(f'Using Firefox profile: {profile_dir.name}', flush=True)
    for lf in ['lock', 'parent.lock', '.parentlock']:
        (profile_dir / lf).unlink(missing_ok=True)
    (profile_dir / 'compatibility.ini').unlink(missing_ok=True)
    try:
        return p.firefox.launch_persistent_context(
            str(profile_dir),
            headless=True,
            firefox_user_prefs={'dom.webdriver.enabled': False},
        )
    except Exception as e:
        raise SystemExit(f'Failed to open Firefox profile: {e}') from e


_CF_REQUIRED_COOKIES = ('AuthorsUser', 'CobaltSession')


def _extract_site_cookies(ctx, site_names: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Returns (cookies, errors) — both keyed by site name."""
    cookies, errors = {}, {}
    for site in site_names:
        if site == 'curseforge':
            found = {c['name']: c['value'] for c in ctx.cookies([_CF_URL])}
            missing = [n for n in _CF_REQUIRED_COOKIES if n not in found]
            if missing:
                names = ', '.join(found.keys()) or 'none'
                errors[site] = (
                    f'Not logged into {site} (found: {names}, missing: {", ".join(missing)}). '
                    f'Log into {_CF_URL} in Firefox, quit Firefox, then re-run puppy auth.'
                )
            else:
                cookies[site] = '; '.join(f'{n}={found[n]}' for n in _CF_REQUIRED_COOKIES)
        elif site == 'planetminecraft':
            found = ctx.cookies([_PMC_URL])
            match = next((c for c in found if 'autologin' in c['name'].lower()), None)
            if not match:
                names = ', '.join(c['name'] for c in found) or 'none'
                errors[site] = (
                    f'Not logged into {site} (cookies found: {names}). '
                    f'Log into {_PMC_URL} in Firefox, quit Firefox, then re-run puppy auth.'
                )
            else:
                cookies[site] = f"{match['name']}={match['value']}"
    return cookies, errors


def _check_missing_tokens(auth: dict, site_names: list[str]) -> None:
    for site in _TOKEN_SITES:
        if site in site_names and not auth.get(site, {}).get('token'):
            print(f'{site} token not set — add to auth.yaml', flush=True)


def _load_auth(puppy_home: Path) -> dict:
    auth_file = puppy_home / 'auth.yaml'
    if auth_file.exists():
        return yaml.safe_load(auth_file.read_text()) or {}
    return {}


def _save_auth(puppy_home: Path, auth: dict) -> None:
    auth_file = puppy_home / 'auth.yaml'
    auth_file.write_text(yaml.dump(auth, default_flow_style=False, allow_unicode=True))
    _ensure_gitignored(puppy_home)
    print(f'Credentials saved to {auth_file}', flush=True)


def _ensure_gitignored(puppy_home: Path) -> None:
    gitignore = puppy_home / '.gitignore'
    lines = gitignore.read_text().splitlines() if gitignore.exists() else []
    if 'auth.yaml' not in lines:
        with gitignore.open('a') as f:
            f.write('\nauth.yaml\n')


def run_auth(site: str | None, directory: Path) -> None:
    puppy_home = find_puppy_home(directory)
    if not puppy_home:
        raise SystemExit(
            f'Cannot find puppy home from {directory}\n'
            'Run from inside a directory named "puppy" that contains puppy.yaml.'
        )
    site_names = _resolve_sites(site, puppy_home)
    auth = _load_auth(puppy_home)

    cookie_sites = [s for s in site_names if s in _COOKIE_SITES]
    if cookie_sites:
        print('Extracting cookies from Firefox…', flush=True)
        with sync_playwright() as p:
            ctx = _open_context(p)
            try:
                cookies, errors = _extract_site_cookies(ctx, cookie_sites)
            finally:
                ctx.close()
        for site_name, cookie_str in cookies.items():
            auth.setdefault(site_name, {})['cookie'] = cookie_str
            print(f'{site_name}: cookie extracted.', flush=True)
        if cookies:
            _save_auth(puppy_home, auth)
        for msg in errors.values():
            print(f'Error: {msg}', flush=True)
        if errors:
            raise SystemExit(1)

    _check_missing_tokens(auth, site_names)
