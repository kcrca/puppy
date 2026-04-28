import tempfile
from pathlib import Path


def test_modrinth_prefers_md_over_html(project_env, run_puppy):
    mr_dir = project_env['project'] / 'modrinth'
    mr_dir.mkdir()
    (mr_dir / 'description.md').write_text('Native Markdown Content')
    (mr_dir / 'description.html').write_text('<h1>Secondary HTML Content</h1>')

    run_puppy('push', '-n', '-s', 'modrinth')

    content = (Path(tempfile.gettempdir()) / 'puppy' / 'neonglow' / 'modrinth' / 'description.md').read_text()
    assert 'Native Markdown Content' in content
    assert '<h1>Secondary HTML Content</h1>' not in content
