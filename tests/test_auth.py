"""Tests for puppy auth cookie harvesting."""
from unittest.mock import MagicMock, patch

import pytest
import yaml

from puppy.auth import run_auth


def _make_cookies(*pairs):
    return [{'name': n, 'value': v} for n, v in pairs]


CF_COOKIES = _make_cookies(('AuthorsUser', 'au-xyz'), ('CobaltSession', 'cf-abc'))
PMC_COOKIES = _make_cookies(('pmc_autologin', 'pmc-xyz'))


def _ctx_mock(cf=CF_COOKIES, pmc=PMC_COOKIES):
    ctx = MagicMock()
    def _cookies(urls):
        url = urls[0] if urls else ''
        if 'curseforge' in url:
            return cf
        if 'planetminecraft' in url:
            return pmc
        return []
    ctx.cookies.side_effect = _cookies
    return ctx


@pytest.fixture()
def auth_run(tmp_path):
    """Returns a helper that calls run_auth with a mocked browser context."""
    def _run(site=None, ctx=None, initial_auth=None):
        if initial_auth:
            (tmp_path / 'puppy.yaml').write_text('')
            (tmp_path / 'auth.yaml').write_text(yaml.dump(initial_auth))
        else:
            (tmp_path / 'puppy.yaml').write_text('')

        mock_ctx = ctx if ctx is not None else _ctx_mock()
        mock_p = MagicMock()
        with (
            patch('puppy.auth._open_context', return_value=mock_ctx),
            patch('puppy.auth.sync_playwright') as mock_pw,
        ):
            mock_pw.return_value.__enter__.return_value = mock_p
            try:
                run_auth(site=site, directory=tmp_path)
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code if isinstance(e.code, int) else 1

        auth_file = tmp_path / 'auth.yaml'
        auth = yaml.safe_load(auth_file.read_text()) if auth_file.exists() else {}
        return auth, exit_code

    return _run


def test_cf_cookie_saved(auth_run):
    auth, code = auth_run(site='cf')
    assert auth['curseforge']['cookie'] == 'AuthorsUser=au-xyz; CobaltSession=cf-abc'
    assert code == 0


def test_existing_data_preserved(auth_run):
    initial = {
        'curseforge': {'token': 'cf-token', 'cookie': 'CobaltSession=old'},
        'modrinth': {'token': 'mr-token'},
    }
    auth, code = auth_run(site='cf', initial_auth=initial)
    assert auth['curseforge']['token'] == 'cf-token'
    assert auth['modrinth']['token'] == 'mr-token'
    assert code == 0


def test_cookie_overwritten(auth_run):
    initial = {'curseforge': {'cookie': 'AuthorsUser=old; CobaltSession=old', 'token': 'cf-token'}}
    auth, code = auth_run(site='cf', initial_auth=initial)
    assert auth['curseforge']['cookie'] == 'AuthorsUser=au-xyz; CobaltSession=cf-abc'
    assert auth['curseforge']['token'] == 'cf-token'


def test_missing_cookie_exits_1(auth_run):
    ctx = _ctx_mock(cf=[], pmc=PMC_COOKIES)
    auth, code = auth_run(site='cf', ctx=ctx)
    assert code == 1


def test_partial_cf_cookies_exits_1(auth_run):
    ctx = _ctx_mock(cf=_make_cookies(('CobaltSession', 'cf-abc')), pmc=PMC_COOKIES)
    auth, code = auth_run(site='cf', ctx=ctx)
    assert code == 1


def test_pmc_failure_saves_cf(auth_run):
    ctx = _ctx_mock(cf=CF_COOKIES, pmc=[])
    auth, code = auth_run(ctx=ctx)
    assert auth.get('curseforge', {}).get('cookie') == 'AuthorsUser=au-xyz; CobaltSession=cf-abc'
    assert code == 1


def test_site_filter_skips_pmc(auth_run):
    ctx = _ctx_mock(cf=CF_COOKIES, pmc=[])
    auth, code = auth_run(site='cf', ctx=ctx)
    assert code == 0
    assert 'planetminecraft' not in auth


def test_missing_token_warning(auth_run, capsys):
    auth_run()
    out = capsys.readouterr().out
    assert 'curseforge token not set' in out
    assert 'modrinth token not set' in out


def test_no_token_warning_for_excluded_site(auth_run, capsys):
    auth_run(site='cf')
    out = capsys.readouterr().out
    assert 'modrinth token not set' not in out


def test_gitignore_updated(auth_run, tmp_path):
    auth_run(site='cf')
    gitignore = tmp_path / '.gitignore'
    assert gitignore.exists()
    assert 'auth.yaml' in gitignore.read_text()
