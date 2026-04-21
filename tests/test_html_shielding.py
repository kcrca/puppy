import tempfile
import yaml
from pathlib import Path


def test_html_tag_translation_pmc(project_env, run_puppy):
    """HTML tags like <u> should be protected and translated to BBCode for PMC."""
    (project_env['source'] / 'puppy.yaml').write_text(yaml.dump({'md_html_tags': ['u', 'b']}))
    (project_env['source'] / 'description.md').write_text(
        'This is <u>underlined</u> and <b>bold</b>.'
    )

    run_puppy('push', '-n', '-s', 'planetminecraft')

    content = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    ).read_text()

    assert '[u]underlined[/u]' in content
    assert '[b]bold[/b]' in content
    assert '<u>' not in content
