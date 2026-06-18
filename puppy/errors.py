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
