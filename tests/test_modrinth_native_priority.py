import tempfile
from pathlib import Path

def test_modrinth_prefers_md_over_html(project_env, run_puppy):
    """
    Verifies that Modrinth prioritizes .md over .html, 
    matching its native format (Native Winner principle).
    """
    mr_dir = project_env["source"] / "modrinth"
    mr_dir.mkdir()
    
    (mr_dir / "description.md").write_text("Native Markdown Content")
    (mr_dir / "description.html").write_text("<h1>Secondary HTML Content</h1>")
    
    # Run for Modrinth
    run_puppy("push", "-n", "-s", "modrinth")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    content = debug_file.read_text()
    
    # Should have picked the .md file
    assert "Native Markdown Content" in content
    assert "<h1>Secondary HTML Content</h1>" not in content
