import tempfile
from pathlib import Path

def test_relative_path_consistency(project_env, run_puppy):
    """
    Spec 5.5: Relative paths in any YAML are resolved relative 
    to the project's puppy/ directory, regardless of file location.
    """
    # Setup: Place an icon in puppy/
    icon_path = project_env["source"] / "my_icon.png"
    icon_path.write_text("fake_image_data")
    
    # Create a deep site-specific config
    site_config_dir = project_env["source"] / "modrinth"
    site_config_dir.mkdir()
    
    # YAML is in puppy/modrinth/, but 'my_icon.png' must resolve to puppy/my_icon.png
    (site_config_dir / "puppy.yaml").write_text("icon: 'my_icon.png'")
    
    # Execution
    run_puppy("push", "-n", "-s", "modrinth")
    
    # Validation: icon is staged at the root of the debug dir, not per-site
    temp_icon = Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "icon.png"
    assert temp_icon.exists()
