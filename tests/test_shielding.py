import tempfile
from pathlib import Path


def test_tag_shielding(project_env, run_puppy):
    """<u> tags should be protected from markdown and converted for PMC."""
    (project_env['source'] / 'description.md').write_text('Underline <u>this</u> text.')

    run_puppy('push', '-n', '-s', 'planetminecraft')

    debug_file = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    )
    # PMC uses [u] instead of <u>
    assert 'Underline [u]this[/u] text.' in debug_file.read_text()
