"""Shared conformance suite — runs the common Site transport contract against
every registered site instance. Site-specific protocol behavior lives in the
per-site test files; this covers what every site must honor identically."""
import io
import urllib.error
from unittest.mock import patch

import pytest

from puppy.errors import AuthExpiredError, SiteError
from puppy.sites import SITES


def _http_error(code: int, body: bytes = b''):
    return urllib.error.HTTPError('https://example.test', code, 'err', {}, io.BytesIO(body))


@pytest.mark.parametrize('site', SITES, ids=lambda s: s.name)
class TestSiteContract:
    def test_send_decodes_json(self, site):
        with patch('puppy.sites.base.urlopen_retrying', return_value=b'{"a": 1}'):
            assert site._send(object()) == {'a': 1}

    def test_send_empty_is_none(self, site):
        with patch('puppy.sites.base.urlopen_retrying', return_value=b''):
            assert site._send(object()) is None

    def test_send_non_json_is_text(self, site):
        with patch('puppy.sites.base.urlopen_retrying', return_value=b'hello'):
            assert site._send(object()) == 'hello'

    def test_send_raises_classified_error(self, site):
        with patch('puppy.sites.base.urlopen_retrying', side_effect=_http_error(500, b'boom')):
            with pytest.raises(SiteError):
                site._send(object())

    def test_auth_failure_on_bare_401(self, site):
        # 401 with no usable body is an expired-auth signal for every site
        assert isinstance(site.classify_http_error(_http_error(401)), AuthExpiredError)

    def test_server_error_is_site_error(self, site):
        assert isinstance(site.classify_http_error(_http_error(503, b'down')), SiteError)


@pytest.mark.parametrize('site', SITES, ids=lambda s: s.name)
class TestSiteMetadata:
    def test_has_project_types(self, site):
        assert site.project_types

    def test_img_tag_contains_url(self, site):
        assert 'http://cdn/x.png' in site.img_tag('http://cdn/x.png', 'x')

    def test_auth_arg_is_str(self, site):
        assert isinstance(site.auth_arg, str)
