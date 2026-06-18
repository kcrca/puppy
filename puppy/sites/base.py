from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, TYPE_CHECKING

from puppy.errors import AuthExpiredError, SiteError
from puppy.http import urlopen_retrying

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext


class Site:
    name: str
    aliases: list[str]
    label: str
    template_ext: str
    desc_exts: list[str]
    auth_arg: str = ''               # value for `puppy auth --site X` in error hints
    required_auth_keys: set[str] | None = None   # auth.yaml keys checked for presence
    project_types: set[str] = set()  # project types this site can publish

    _AUTH_URL: str = ''

    def supports(self, project_type: str) -> bool:
        return project_type in self.project_types

    def classify_http_error(self, e: urllib.error.HTTPError) -> Exception:
        """Map an HTTPError to AuthExpiredError or SiteError.

        Default: 401/403 are auth failures, everything else is a generic error.
        Sites whose API overloads these codes override this.
        """
        body = e.read().decode(errors='replace')
        if e.code in (401, 403):
            return AuthExpiredError(e.code, body)
        return SiteError(e.code, body)

    def _send(self, req: urllib.request.Request, *, timeout: int = 30) -> Any:
        """Shared transport: retry on 429/503, classify failures, decode JSON (else raw text)."""
        try:
            body = urlopen_retrying(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            raise self.classify_http_error(e)
        if not body:
            return None
        try:
            return json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return body.decode()

    def assigned_id(self, config: dict):
        """The site-assigned project id (present only once the project exists)."""
        return config.get(self.name, {}).get('id')

    def ref(self, config: dict):
        """The id used to address an existing project for push/pull."""
        return self.assigned_id(config)

    def has_credentials(self, auth: dict) -> bool:
        """Whether auth.yaml holds the credentials this site needs to act."""
        return True

    def extract_cookies(self, ctx: BrowserContext) -> tuple[str | None, str | None]:
        """Pull this site's login cookie from a browser context.

        Returns (cookie_string, error_message); at most one is non-None.
        Sites that authenticate by cookie override this; the default (token-only
        or no auth) returns (None, None). Overriding marks a site as cookie-based.
        """
        return None, None

    def _login_error(self, detail: str) -> str:
        return (
            f'Not logged into {self.name} ({detail}). '
            f'Log into {self._AUTH_URL} in Firefox, quit Firefox, then re-run puppy auth.'
        )

    def missing_token_warning(self, auth: dict) -> str | None:
        """Warning if this site needs an API token that is absent from auth.yaml.

        Token-based sites override this (typically `return self._token_warning(auth)`);
        the default (no token) returns None.
        """
        return None

    def _token_warning(self, auth: dict) -> str | None:
        if not auth.get(self.name, {}).get('token'):
            return f'{self.name} token not set — add to auth.yaml'
        return None

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

    def resolve_id(self, config: dict, auth: dict, verbosity: int) -> dict:
        return config

    def post_upload(self, puppy_dir: Path, version: str) -> None:
        pass

    def apply_settings(self, settings: dict, sc: dict) -> None:
        pass

    def spdx_license(self, value: str) -> str | None:
        return value

    def auth_yaml_entry(self) -> str:
        return ''

    def puppy_yaml_entry(self, pack: str) -> str:
        return f'{self.name}:\n  id: null\n  slug: {pack}\n'

    def init_template(self) -> tuple[str, str]:
        raise NotImplementedError

    def img_tag(self, url: str, name: str) -> str:
        return f'<img src="{url}" alt="{name}">'

    def img_tag_md(self, url: str, name: str) -> str:
        return self.img_tag(url, name)

    def upload_images(
        self,
        project_id,
        auth: dict,
        image_list: list,
        images_dir: Path,
        verbosity: int,
        project_type: str = 'pack',
        changed: set = None,
    ) -> dict[str, str]:
        return {}

    def upload_icon(self, project_id, auth: dict, icon_bytes: bytes) -> str | None:
        """Upload the project icon, returning a CDN URL if the site provides one."""
        return None

    def gallery_urls(self, project_id, auth: dict, project_type: str = 'pack') -> dict[str, str]:
        """Map of image-name stem → CDN URL for the existing gallery, without uploading."""
        return {}

    def file_changed(self, project_id, auth: dict, local_sha: str, site_store: dict, hash_file: str) -> bool:
        """Whether the local artifact differs from what was last pushed for this site."""
        return site_store.get('file') != local_sha

    def upload_artifact(self, project_id, auth: dict, zip_path: Path, version: str,
                        config: dict, puppy_dir: Path, verbosity: int) -> None:
        """Upload the version artifact to this site and record post-upload state."""
        raise NotImplementedError

    def create_project(self, *, config: dict, auth: dict, icon_bytes: bytes,
                       image_list: list, images_dir: Path, verbosity: int) -> dict:
        """Create the project on this site, taking only the inputs it needs."""
        raise NotImplementedError

    def url_for(self, site_config: dict) -> str | None:
        raise NotImplementedError
