import pytest


@pytest.fixture
def puppy_env(tmp_path):
    """
    Sets up the standard dual-layer directory structure:
      <tmp>/puppy/                           (Global puppy home)
      <tmp>/puppy/NeonGlow/                  (Project root)
      <tmp>/puppy/NeonGlow/puppy/            (Project puppy dir)
      <tmp>/puppy/NeonGlow/puppy/curseforge/ (Project site dir)
    """
    home = tmp_path / "puppy"
    home.mkdir()

    project_root = home / "NeonGlow"
    project_root.mkdir()

    project_puppy = project_root / "puppy"
    project_puppy.mkdir()

    project_cf = project_puppy / "curseforge"
    project_cf.mkdir()

    return {
        "home": home,
        "project_root": project_root,
        "project_puppy": project_puppy,
        "project_cf": project_cf,
    }
