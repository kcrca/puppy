import tempfile
from pathlib import Path

def test_variable_priority(project_env, run_puppy):
    (project_env["home"] / "puppy.yaml").write_text("val: 'global'")
    (project_env["source"] / "puppy.yaml").write_text("val: 'project'")
    (project_env["source"] / "description.md").write_text("{{ val }}")
    
    run_puppy("push", "-n")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    assert "project" in debug_file.read_text()
