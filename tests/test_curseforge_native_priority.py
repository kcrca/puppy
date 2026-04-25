import tempfile
from pathlib import Path

def test_curseforge_prefers_html_over_md(project_env, run_puppy):
    """
    Verifies that CurseForge still prioritizes .html over .md for its native format.
    """
    cf_dir = project_env["project"] / "curseforge"
    cf_dir.mkdir()
    
    (cf_dir / "description.md").write_text("Markdown Content")
    (cf_dir / "description.html").write_text("<h1>Native HTML Content</h1>")
    
    run_puppy("push", "-n", "-s", "curseforge")
    
    # Note: Staged for worker as .html
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "curseforge" / "description.html"
    content = debug_file.read_text()
    
    # Should have picked the .html file
    assert "<h1>Native HTML Content</h1>" in content
    assert "Markdown Content" not in content
