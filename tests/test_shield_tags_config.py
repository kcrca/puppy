import tempfile
from pathlib import Path


def test_custom_md_html_tags_replaces_defaults(project_env, run_puppy):
    """md_html_tags in puppy.yaml should replace the default ['u'] list.
    'b' should be converted to BBCode for PMC; 'u' should be left as HTML since
    it's no longer in the list."""
    (project_env["source"] / "puppy.yaml").write_text("md_html_tags:\n  - b\n")
    (project_env["source"] / "description.md").write_text(
        "Text <u>underline</u> and <b>bold</b> words."
    )

    run_puppy("push", "-n", "-s", "planetminecraft")

    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "planetminecraft" / "description.bbcode"
    content = debug_file.read_text()

    assert "[b]bold[/b]" in content
    assert "<u>underline</u>" in content
