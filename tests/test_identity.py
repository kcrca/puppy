import pytest


def test_automatic_name_casing(puppy_env):
    from puppy.core import Project

    # MixedCase directory — name preserved, pack lowercased
    p1 = Project(puppy_env["project_root"])
    assert p1.name == "NeonGlow"
    assert p1.pack == "neonglow"

    # Lowercase directory — name title-cased, pack unchanged
    low_dir = puppy_env["home"] / "clean"
    low_dir.mkdir()
    p2 = Project(low_dir)
    assert p2.name == "Clean"
    assert p2.pack == "clean"


def test_override_name_only(puppy_env):
    from puppy.core import Project

    p = Project(puppy_env["project_root"], override_name="NeonGlow")
    assert p.name == "NeonGlow"
    assert p.pack == "neonglow"  # derived from name


def test_override_pack_only(puppy_env):
    from puppy.core import Project

    # Lowercase pack — name should be title-cased
    p1 = Project(puppy_env["project_root"], override_pack="clean")
    assert p1.pack == "clean"
    assert p1.name == "Clean"

    # Mixed-case pack — name should be preserved as-is
    p2 = Project(puppy_env["project_root"], override_pack="NeonGlow")
    assert p2.pack == "NeonGlow"
    assert p2.name == "NeonGlow"


def test_override_both(puppy_env):
    from puppy.core import Project

    p = Project(puppy_env["project_root"], override_name="My Pack", override_pack="mypack")
    assert p.name == "My Pack"
    assert p.pack == "mypack"


def test_from_config_writes_back_missing_fields(puppy_env):
    from puppy.core import Project
    import yaml

    puppy_yaml = puppy_env["project_puppy"] / "puppy.yaml"

    # Only name provided — pack should be derived and written back
    puppy_yaml.write_text("name: NeonGlow\n")
    p = Project.from_config(puppy_env["project_root"], {"name": "NeonGlow"})
    assert p.pack == "neonglow"
    config = yaml.safe_load(puppy_yaml.read_text())
    assert config["pack"] == "neonglow"

    # Only pack provided — name should be derived and written back
    puppy_yaml.write_text("pack: clean\n")
    p2 = Project.from_config(puppy_env["project_root"], {"pack": "clean"})
    assert p2.name == "Clean"
    config2 = yaml.safe_load(puppy_yaml.read_text())
    assert config2["name"] == "Clean"