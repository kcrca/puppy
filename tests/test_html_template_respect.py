import tempfile
from pathlib import Path

def test_site_specific_body_override(project_env, run_puppy):
    """modrinth/description.md overrides generic description.md for Modrinth."""
    mr_dir = project_env["source"] / "modrinth"
    mr_dir.mkdir()
    (mr_dir / "body.md").write_text("Modrinth-specific body with <span id='test'>content</span>.")
    (project_env["source"] / "description.md").write_text("Generic body, should not appear.")

    run_puppy("push", "-n", "-s", "modrinth")

    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    content = debug_file.read_text()

    assert "Modrinth-specific body" in content
    assert "<span id='test'>content</span>" in content
    assert "Generic body" not in content
