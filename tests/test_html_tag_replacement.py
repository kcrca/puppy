import tempfile
import yaml
from pathlib import Path


def test_html_tags_replacement_logic(project_env, run_puppy):
    """Setting md_html_tags to ['b'] means <u> should no longer be shielded/translated."""
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'md_html_tags': ['b']}))
    (project_env['project'] / 'description.md').write_text('<u>Ignore</u> and <b>Protect</b>.')

    run_puppy('push', '-n', '-s', 'planetminecraft')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    ).read_text()

    assert '[b]Protect[/b]' in content
    assert '<u>Ignore</u>' in content
    assert '[u]' not in content
