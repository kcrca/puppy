import tempfile
from pathlib import Path

def test_dry_run_html_index_creation(project_env, run_puppy):
    """A dry run must generate a central index.html preview page."""
    run_puppy("push", "-n")
    
    debug_index = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "index.html"
    assert debug_index.exists()
    content = debug_index.read_text()
    assert "<html" in content
    assert "Modrinth" in content
    assert "CurseForge" in content
