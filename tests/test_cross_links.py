import tempfile
from pathlib import Path

def test_sibling_links(project_env, run_puppy):
    other = project_env["home"] / "Other"
    (other / "puppy").mkdir(parents=True)
    (other / "puppy" / "puppy.yaml").write_text("pack: 'other'\nmodrinth: {slug: 'other-slug'}")
    
    (project_env["home"] / "puppy.yaml").write_text("projects: [NeonGlow, Other]")
    (project_env["source"] / "description.md").write_text("Link: {{ projects.other.modrinth.url }}")
    
    run_puppy("push", "-n", "-s", "modrinth")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    assert "https://modrinth.com/mod/other-slug" in debug_file.read_text()
