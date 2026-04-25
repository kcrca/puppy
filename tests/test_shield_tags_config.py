import tempfile
import yaml
from pathlib import Path


def test_custom_md_html_tags_replaces_defaults(project_env, run_puppy):
    """md_html_tags in puppy.yaml should replace the default ['u'] list."""
    (project_env['project'] / 'puppy.yaml').write_text(yaml.dump({'md_html_tags': ['b']}))
    (project_env['project'] / 'description.md').write_text(
        'Text <u>underline</u> and <b>bold</b> words.'
    )

    run_puppy('push', '-n', '-s', 'planetminecraft')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    ).read_text()

    assert '[b]bold[/b]' in content
    assert '<u>underline</u>' in content
