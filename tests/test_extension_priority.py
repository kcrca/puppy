import tempfile
from pathlib import Path

def test_site_extension_priority_html_wins(project_env, run_puppy):
    """For Modrinth, .html should be preferred over .md if both exist in the site folder."""
    mr_dir = project_env["source"] / "modrinth"
    mr_dir.mkdir()
    
    (mr_dir / "body.md").write_text("Markdown Version")
    (mr_dir / "body.html").write_text("<h1>HTML Version</h1>")
    
    run_puppy("push", "-n", "-s", "modrinth")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    assert "<h1>HTML Version</h1>" in debug_file.read_text()
