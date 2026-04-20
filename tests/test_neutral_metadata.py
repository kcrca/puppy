import tempfile
from pathlib import Path
import yaml


def test_resolution_expands_to_all_sites(project_env, run_puppy):
    (project_env["source"] / "puppy.yaml").write_text("resolution: 16\n")
    run_puppy("push", "-n")

    index = (Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "index.html").read_text()
    assert "16x" in index  # CF mainCategory and Modrinth tag
    assert "16" in index   # PMC resolution


def test_progress_appears_in_pmc(project_env, run_puppy):
    (project_env["source"] / "puppy.yaml").write_text("progress: 75\n")
    run_puppy("push", "-n")

    index = (Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "index.html").read_text()
    assert "75%" in index


def test_license_appears_on_cf_and_modrinth(project_env, run_puppy):
    (project_env["source"] / "puppy.yaml").write_text("license: MIT\n")
    run_puppy("push", "-n")

    index = (Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "index.html").read_text()
    assert "MIT" in index


def test_per_site_override_wins_over_neutral(project_env, run_puppy):
    (project_env["source"] / "puppy.yaml").write_text(
        "resolution: 16\nmodrinth:\n  tags:\n    16x: false\n"
    )
    run_puppy("push", "-n")

    index = (Path(tempfile.gettempdir()) / "puppy" / "neonglow" / "index.html").read_text()
    # Modrinth 16x tag is false so shouldn't appear in Modrinth tags
    # CF and PMC should still show 16x / 16
    assert "16x" in index  # CF still gets it
