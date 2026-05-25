import yaml

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
