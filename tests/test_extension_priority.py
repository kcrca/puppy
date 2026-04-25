import tempfile
from pathlib import Path

def test_site_extension_priority_native_wins(project_env, run_puppy):
    """For Modrinth, .md is preferred over .html when both exist — native format wins."""
    mr_dir = project_env["project"] / "modrinth"
    mr_dir.mkdir()

    (mr_dir / "description.md").write_text("Markdown Version")
    (mr_dir / "description.html").write_text("<h1>HTML Version</h1>")

    run_puppy("push", "-n", "-s", "modrinth")

    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    assert "Markdown Version" in debug_file.read_text()
