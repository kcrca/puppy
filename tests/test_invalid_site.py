from puppy.sites import SiteVisitor


def test_invalid_site_raises(project_env, run_puppy):
    result = run_puppy('push', '-n', '--site', 'invalid_site')
    assert result != 0


def test_valid_site_abbreviation_accepted(project_env, run_puppy):
    result = run_puppy('push', '-n', '--site', 'mr')
    assert result is None or result == 0


def test_unknown_site_in_visitor_raises():
    try:
        SiteVisitor('notasite')
        assert False, 'expected SystemExit'
    except SystemExit as e:
        assert 'Unknown' in str(e)


def test_unknown_project_type_raises():
    try:
        SiteVisitor(project_type='plugin')
        assert False, 'expected SystemExit'
    except SystemExit as e:
        assert 'Unknown type' in str(e)


def test_unsupported_project_type_with_explicit_site_raises():
    try:
        SiteVisitor('pmc', project_type='mod')
        assert False, 'expected SystemExit'
    except SystemExit as e:
        assert 'do not support' in str(e)
        assert 'mod' in str(e)


def test_pack_type_includes_all_sites():
    visitor = SiteVisitor(project_type='pack')
    from puppy.sites import SITES
    assert list(visitor) == SITES
