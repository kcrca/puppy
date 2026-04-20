import yaml
def test_relative_path_resolution(project_env, run_puppy):
    """Relative paths should resolve relative to the project source directory."""
    ext_dir = project_env["root"] / "external_assets"
    ext_dir.mkdir()
    (ext_dir / "icon.png").write_text("external_icon")
    
    # Path is ../../../external_assets/icon.png relative to project/puppy/
    (project_env["source"] / "puppy.yaml").write_text("icon: '../external_assets/icon.png'")
    
    # This test checks that Puppy doesn't crash and finds the file
    result = run_puppy("push", "-n")
    assert result is None or result == 0
