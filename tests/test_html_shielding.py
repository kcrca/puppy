import tempfile
from pathlib import Path

def test_html_tag_translation_pmc(project_env, run_puppy):
    """HTML tags like <u> should be protected and translated to BBCode for PMC."""
    # Set custom tags to shield in puppy.yaml
    (project_env["source"] / "puppy.yaml").write_text("md_html_tags: ['u', 'b']")
    (project_env["source"] / "description.md").write_text("This is <u>underlined</u> and <b>bold</b>.")
    
    run_puppy("push", "-n", "-s", "planetminecraft")
    
    debug_path = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "planetminecraft" / "description.bbcode"
    content = debug_path.read_text()
    
    # Should be translated to PMC's BBCode format
    assert "[u]underlined[/u]" in content
    assert "[b]bold[/b]" in content
    assert "<u>" not in content
