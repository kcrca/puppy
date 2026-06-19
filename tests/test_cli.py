import pytest

from puppy.cli import main


def test_rehash_rejected_with_non_push_action():
    with pytest.raises(SystemExit):
        main(['--rehash', 'pull'])


def test_rehash_rejected_with_dry_run():
    with pytest.raises(SystemExit):
        main(['--rehash', '--dry-run'])


def test_version_flag_removed():
    # -V/--version was removed; version comes from puppy.yaml
    with pytest.raises(SystemExit):
        main(['push', '--version', '1.0'])
    with pytest.raises(SystemExit):
        main(['push', '-V', '1.0'])


def test_force_flag_removed():
    # -f/--force was removed (create has no confirmation prompt)
    with pytest.raises(SystemExit):
        main(['create', '-f'])
    with pytest.raises(SystemExit):
        main(['create', '--force'])
