import pytest
from unittest.mock import MagicMock, patch

from puppy.errors import prefix_site_error


# ── prefix_site_error ─────────────────────────────────────────────────────────

def test_prefix_site_error_adds_label():
    e = prefix_site_error('Modrinth', SystemExit('project not found'))
    assert str(e) == '[Modrinth] project not found'


def test_prefix_site_error_no_double_prefix():
    e = prefix_site_error('Modrinth', SystemExit('[Modrinth] already prefixed'))
    assert str(e) == '[Modrinth] already prefixed'


def test_prefix_site_error_other_bracket_prefix_unchanged():
    e = prefix_site_error('CurseForge', SystemExit('[OtherSite] message'))
    assert str(e) == '[OtherSite] message'


# ── puller: resolve_ids wraps errors ─────────────────────────────────────────

# ── puller: errors get site label ────────────────────────────────────────────

def _make_project(tmp_path):
    p = MagicMock()
    p.puppy_dir = tmp_path
    p.name = 'Test'
    return p


def test_pull_resolve_ids_prefixes_site_label(tmp_path):
    from puppy.puller import _resolve_ids
    from puppy.sites import MODRINTH

    config = {'modrinth': {'id': 'abc123'}}
    auth = {'modrinth': {'token': 'tok'}}

    with patch.object(MODRINTH, 'resolve_id', side_effect=SystemExit('slug not found')):
        with pytest.raises(SystemExit, match=r'\[Modrinth\] slug not found'):
            _resolve_ids(config, auth, 'modrinth', 0)


def test_pull_mr_error_gets_site_label(tmp_path):
    from puppy.puller import run_pull

    config = {'modrinth': {'id': 'abc123'}}
    auth = {'modrinth': {'token': 'tok'}}

    with patch('puppy.puller._resolve_ids', return_value=config), \
         patch('puppy.puller._run_pull', side_effect=SystemExit('API error')):
        with pytest.raises(SystemExit, match=r'\[Modrinth\] API error'):
            run_pull(project=_make_project(tmp_path), config=config, auth=auth,
                     site='modrinth', images=False, verbosity=0)


def test_pull_cf_error_gets_site_label(tmp_path):
    from puppy.puller import run_pull

    config = {'curseforge': {'id': 99}}
    auth = {'curseforge': {'token': 'tok', 'cookie': 'c=1'}}

    with patch('puppy.puller._resolve_ids', return_value=config), \
         patch('puppy.puller._run_pull', side_effect=SystemExit('CF error')):
        with pytest.raises(SystemExit, match=r'\[CurseForge\] CF error'):
            run_pull(project=_make_project(tmp_path), config=config, auth=auth,
                     site='cf', images=False, verbosity=0)


def test_pull_pmc_error_gets_site_label(tmp_path):
    from puppy.puller import run_pull

    config = {'planetminecraft': {'id': 55}}
    auth = {'planetminecraft': 'cookie=val'}

    with patch('puppy.puller._resolve_ids', return_value=config), \
         patch('puppy.puller._run_pull', side_effect=SystemExit('PMC error')):
        with pytest.raises(SystemExit, match=r'\[PlanetMinecraft\] PMC error'):
            run_pull(project=_make_project(tmp_path), config=config, auth=auth,
                     site='pmc', images=False, verbosity=0)
