import tempfile
from pathlib import Path

def test_content_discovery_cascade(project_env, run_puppy):
    """Tests the 5-layer cascade defined in section 5.2 of the spec."""
    # 1. Global General Fragment (Level 5)
    (project_env["home"] / "footer.md").write_text("Global Footer")
    
    # 2. Project General Fragment (Level 3)
    (project_env["source"] / "header.md").write_text("Project Header")
    
    # 3. Project Site Override (Level 2)
    mr_dir = project_env["source"] / "modrinth"
    mr_dir.mkdir()
    (mr_dir / "header.md").write_text("Modrinth-Only Header")
    
    (project_env["source"] / "description.md").write_text(
        "{{ snippet:header }}\nBody Content\n{{ snippet:footer }}"
    )
    
    run_puppy("push", "-n", "-s", "modrinth")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    content = debug_file.read_text()
    
    assert "Modrinth-Only Header" in content
    assert "Global Footer" in content
    assert "Project Header" not in content
