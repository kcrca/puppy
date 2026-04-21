import yaml
from pathlib import Path

def test_name_to_slug_derivation_and_writeback(project_env, run_puppy):
    """
    Spec 2: If only 'name' is provided, 'pack' is derived and written back.
    Ensures special characters like '!' and spaces are stripped for the slug.
    """
    # Create a puppy.yaml with only a complex name
    config_path = project_env["source"] / "puppy.yaml"
    config_path.write_text("name: 'Super Pack!'")
    
    # Run an action (like push -n) to trigger discovery
    run_puppy("push", "-n", "-s", "modrinth")
    
    # Check the updated puppy.yaml
    updated_config = yaml.safe_load(config_path.read_text())
    
    # The name must be preserved exactly
    assert updated_config['name'] == "Super Pack!"
    
    # The pack slug should have been derived and written back
    # It should be clean for URLs/Folders (lowercase, no '!')
    assert "pack" in updated_config
    assert updated_config['pack'] == "superpack"
