import subprocess
from pathlib import Path

import pytest

from puppy.runner import _worker_prep


@pytest.fixture
def fake_worker(tmp_path):
    """A minimal git repo that simulates the PackUploader worker."""
    d = tmp_path / 'worker'
    d.mkdir()
    subprocess.run(['git', 'init', '-b', 'main'], cwd=d, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=d, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=d, check=True, capture_output=True)
    (d / 'settings.json').write_text('{}')
    (d / '.gitignore').write_text('node_modules/\n')
    (d / 'node_modules').mkdir()
    subprocess.run(['git', 'add', '.'], cwd=d, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=d, check=True, capture_output=True)
    return d


def test_clean_removes_untracked_file(fake_worker):
    (fake_worker / 'untracked.txt').write_text('stray file')
    _worker_prep(fake_worker, verbosity=0)
    assert not (fake_worker / 'untracked.txt').exists()


def test_clean_resets_modified_file(fake_worker):
    (fake_worker / 'settings.json').write_text('{"dirty": true}')
    _worker_prep(fake_worker, verbosity=0)
    assert (fake_worker / 'settings.json').read_text() == '{}'


def test_clean_action_via_cli(tmp_path, monkeypatch, fake_worker):
    import puppy.__main__

    monkeypatch.setattr('sys.argv', ['puppy', 'clean', '--worker', str(fake_worker)])
    monkeypatch.setattr('puppy.runner.check_preflight', lambda: None)

    (fake_worker / 'stray.txt').write_text('noise')
    puppy.__main__.main()
    assert not (fake_worker / 'stray.txt').exists()
