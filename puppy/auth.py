"""Cookie harvesting for puppy auth command."""
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

from puppy.core import find_puppy_home
from puppy.sites import SITE_MAP, Site, _ALIASES

_ALL_SITES = set(SITE_MAP)


def _resolve_sites(site: str | None, puppy_home: Path | None = None) -> list[str]:
    if not site:
        if puppy_home:
            puppy_yaml = puppy_home / 'puppy.yaml'
            if puppy_yaml.exists():
                try:
                    config = yaml.safe_load(puppy_yaml.read_text()) or {}
                except yaml.YAMLError as e:
                    raise SystemExit(f'{puppy_yaml}: {e}')
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


def _extract_site_cookies(ctx, site_names: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Returns (cookies, errors) — both keyed by site name."""
    cookies, errors = {}, {}
    for site in site_names:
        cookie, error = SITE_MAP[site].extract_cookies(ctx)
        if error:
            errors[site] = error
        elif cookie:
            cookies[site] = cookie
    return cookies, errors


def _check_missing_tokens(auth: dict, site_names: list[str]) -> None:
    for site in site_names:
        warning = SITE_MAP[site].missing_token_warning(auth)
        if warning:
            print(warning, flush=True)


def _load_auth(puppy_home: Path) -> dict:
    auth_file = puppy_home / 'auth.yaml'
    if auth_file.exists():
        try:
            return yaml.safe_load(auth_file.read_text()) or {}
        except yaml.YAMLError as e:
            raise SystemExit(f'{auth_file}: {e}')
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

    cookie_sites = [
        s for s in site_names
        if type(SITE_MAP[s]).extract_cookies is not Site.extract_cookies
    ]
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
