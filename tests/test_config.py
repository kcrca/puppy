import pytest

def test_config_synthesis_logic(puppy_env):
    """Ensures strings are merged additively and scalars are overwritten."""
    from puppy.config import ConfigSynthesizer
    
    # Global Config
    (puppy_env["home"] / "puppy.yaml").write_text("""
version: '0.1'
strings:
  footer: 'Global Footer'
""")
    
    # Project Config
    (puppy_env["project_puppy"] / "puppy.yaml").write_text("""
version: '1.2'
strings:
  header: 'Project Header'
""")
    
    synth = ConfigSynthesizer(puppy_env["home"], puppy_env["project_root"])
    config = synth.get_running_config()
    
    assert config["version"] == "1.2"  # Overwritten
    assert config["strings"]["footer"] == "Global Footer"  # Merged from Global
    assert config["strings"]["header"] == "Project Header"  # Merged from Project