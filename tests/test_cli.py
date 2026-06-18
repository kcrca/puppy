import pytest

from puppy.cli import main


def test_rehash_rejected_with_non_push_action():
    with pytest.raises(SystemExit):
        main(['--rehash', 'pull'])


def test_rehash_rejected_with_dry_run():
    with pytest.raises(SystemExit):
        main(['--rehash', '--dry-run'])
