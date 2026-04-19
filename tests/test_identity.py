import pytest

def test_automatic_name_casing(puppy_env):
    from puppy.core import Project
    
    # MixedCase directory
    p1 = Project(puppy_env["project_root"])
    assert p1.name == "NeonGlow"
    assert p1.pack == "neonglow"
    
    # Lowercase directory
    low_dir = puppy_env["home"] / "clean"
    low_dir.mkdir()
    p2 = Project(low_dir)
    assert p2.name == "Clean"
    assert p2.pack == "clean"