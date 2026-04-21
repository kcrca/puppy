import tempfile
from pathlib import Path
import yaml

def test_project_name_with_spaces_and_special_chars(project_env, run_puppy):
    """
    Spec 2: Preserves casing and special characters in 'name'.
    Verifies that 'Neon Glow!' is handled correctly and used in templates.
    """
    # Create project with spaces and exclamation mark in puppy.yaml
    # We'll use a standard slug for the folder but a complex display name
    (project_env["source"] / "puppy.yaml").write_text("name: 'Neon Glow!'\nstatus: 'online'")
    (project_env["source"] / "description.md").write_text("Welcome to {{ name }}.")
    
    run_puppy("push", "-n", "-s", "modrinth")
    
    debug_root = Path(tempfile.gettempdir()) / "puppy" / "neonglow"
    
    # 1. Verify metadata.yaml contains the exact name string
    mr_meta = yaml.safe_load((debug_root / "modrinth" / "metadata.yaml").read_text())
    assert mr_meta['name'] == "Neon Glow!"
    
    # 2. Verify Jinja2 rendered the name correctly in the description
    content = (debug_root / "modrinth" / "description.md").read_text()
    assert "Welcome to Neon Glow!." in content

def test_auto_derived_name_from_directory_with_special_chars(project_env, run_puppy):
    """
    Verifies that if the directory itself has spaces or '!', 
    Puppy derives the name and pack slug correctly.
    """
    # Create a new project directory with special chars
    special_dir = project_env["home"] / "Cool Pack!"
    (special_dir / "puppy").mkdir(parents=True)
    # No puppy.yaml content, let it derive from dir
    (special_dir / "puppy" / "description.md").write_text("Name: {{ name }}")
    
    # Run in the specific project dir
    import os
    os.chdir(special_dir)
    run_puppy("push", "-n", "-s", "modrinth")
    
    # Pack slug should be 'coolpack' (stripped), Name should be 'Cool Pack!'
    debug_root = Path(tempfile.gettempdir()) / "puppy" / "coolpack"
    content = (debug_root / "modrinth" / "description.md").read_text()
    
    assert "Name: Cool Pack!" in content
