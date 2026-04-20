import yaml
def test_project_wins_over_global(project_env, run_puppy):
    """Project source puppy.yaml should override global puppy.yaml"""
    (project_env["home"] / "puppy.yaml").write_text("title: 'Global Title'")
    (project_env["source"] / "puppy.yaml").write_text("title: 'Project Title'")
    
    (project_env["source"] / "description.md").write_text("{{ title }}")
    run_puppy("push", "-n")
    
    import tempfile
    from pathlib import Path
    debug_file = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "modrinth" / "description.md"
    assert "Project Title" in debug_file.read_text()
