import tempfile
from pathlib import Path


def _snapshot_mtimes(directory: Path) -> dict:
    return {p: p.stat().st_mtime for p in directory.rglob('*') if p.is_file()}


def test_dry_run_modifies_no_project_files(project_env, run_puppy):
    """push -n must not write to any project files."""
    before = _snapshot_mtimes(project_env['root'])
    run_puppy('push', '-n')
    after = _snapshot_mtimes(project_env['root'])
    assert before == after, f'Files modified: {[k for k in after if after[k] != before.get(k)]}'


def test_dry_run_html_index_creation(project_env, run_puppy):
    """A dry run must generate a central index.html preview page."""
    run_puppy('push', '-n')

    debug_index = Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'index.html'
    assert debug_index.exists()
    content = debug_index.read_text()
    assert '<html' in content
    assert 'Modrinth' in content
    assert 'CurseForge' in content
