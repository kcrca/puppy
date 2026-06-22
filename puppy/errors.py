README_AUTH_URL = 'https://github.com/kcrca/puppy#authentication-authyaml'


def auth_expired_exit(label: str, auth_arg: str, code: int = None) -> SystemExit:
    """The standard, actionable message for an expired site login (usually a lapsed cookie)."""
    code_part = f' (HTTP {code})' if code else ''
    return SystemExit(
        f'{label} auth expired{code_part} — your saved login has likely expired. '
        f'Refresh it with: puppy auth --site {auth_arg}  '
        f'(cookie setup: {README_AUTH_URL})'
    )


def prefix_site_error(label: str, e: SystemExit) -> SystemExit:
    msg = str(e)
    if msg.startswith('[') or label in msg:
        return e
    return SystemExit(f'[{label}] {msg}')


class AuthExpiredError(Exception):
    def __init__(self, code: int, body: str):
        self.code = code
        self.body = body
        super().__init__(body)


def _site_error_detail(body: str) -> str:
    stripped = body.strip()
    if stripped.startswith('<'):
        return ''
    return f': {stripped[:300]}' if stripped else ''


class SiteError(Exception):
    def __init__(self, code: int, body: str):
        self.code = code
        self.body = body
        super().__init__(f'HTTP {code}{_site_error_detail(body)}')
