import tempfile
from pathlib import Path
import yaml

def test_slug_sanitization_rules(project_env, run_puppy):
    """
    Ensures that 'Neon Glow!' generates a clean slug for folders
    but keeps the '!' in the site metadata.
    """
    (project_env["source"] / "puppy.yaml").write_text("name: 'Neon Glow!'")
    
    # We run the push; Puppy should derive 'neonglow' or 'neon-glow' as the pack slug
    run_puppy("push", "-n", "-s", "modrinth")
    
    # Check the debug output directory
    temp_root = Path(tempfile.gettempdir()) / "puppy"
    
    # The folder should be sanitized (no spaces or exclamation marks)
    # Based on Spec 2: pack is derived as name.lower(). 
    # We expect internal logic to strip the '!' for the file system path.
    possible_slugs = ["neonglow", "neon-glow"]
    assert any((temp_root / slug).exists() for slug in possible_slugs)
    
    # The metadata sent to the API must still have the exclamation mark
    # Finding the actual folder created:
    actual_slug = "neonglow" if (temp_root / "neonglow").exists() else "neon-glow"
    meta = yaml.safe_load((temp_root / actual_slug / "modrinth" / "metadata.yaml").read_text())
    
    assert meta['name'] == "Neon Glow!"
