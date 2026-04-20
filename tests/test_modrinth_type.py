import tempfile
from pathlib import Path

def test_modrinth_url_type_override(project_env, run_puppy):
    """Setting modrinth.type should change the URL structure from /mod/ to /modpack/."""
    (project_env["source"] / "puppy.yaml").write_text(
        "modrinth:\n  slug: 'my-pack'\n  type: 'modpack'"
    )
    (project_env["source"] / "description.md").write_text("URL: {{ projects.neonglow.modrinth.url }}")
    
    run_puppy("push", "-n", "-s", "modrinth")
    
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    assert "https://modrinth.com/modpack/my-pack" in debug_file.read_text()
