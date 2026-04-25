import tempfile
from pathlib import Path

def test_pmc_prefers_bbcode_over_md(project_env, run_puppy):
    """
    Spec 5.2: For PMC, extension priority is (.bbcode -> .md).
    Verifies that native BBCode overrides generic Markdown.
    """
    pmc_dir = project_env["source"] / "planetminecraft"
    pmc_dir.mkdir()
    
    (pmc_dir / "description.md").write_text("Markdown Fallback")
    (pmc_dir / "description.bbcode").write_text("[b]Native PMC BBCode[/b]")
    
    run_puppy("push", "-n", "-s", "planetminecraft")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "planetminecraft" / "description.bbcode"
    content = debug_file.read_text()
    
    # Should have picked the .bbcode file
    assert "[b]Native PMC BBCode[/b]" in content
    assert "Markdown Fallback" not in content
