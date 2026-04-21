import tempfile
from pathlib import Path


def test_html_tags_replacement_logic(project_env, run_puppy):
    """
    If the user defines md_html_tags, it should replace the default ['u'].
    Setting it to ['b'] means <u> should no longer be shielded/translated.
    """
    # Override default ['u'] with only ['b']
    (project_env['source'] / 'puppy.yaml').write_text("md_html_tags: ['b']")

    # Body containing both tags
    (project_env['source'] / 'description.md').write_text(
        '<u>Ignore</u> and <b>Protect</b>.'
    )

    # Run for PMC to verify translation/shielding behavior
    run_puppy('push', '-n', '-s', 'planetminecraft')

    debug_path = (
        Path(tempfile.gettempdir())
        / 'puppy'
        / 'neonglow'
        / 'planetminecraft'
        / 'description.bbcode'
    )
    content = debug_path.read_text()

    # <b> is the new shielded tag, so it should be translated to [b]
    assert '[b]Protect[/b]' in content
    # <u> was replaced/dropped from the set, so it should remain raw <u>
    assert '<u>Ignore</u>' in content
    assert '[u]' not in content
